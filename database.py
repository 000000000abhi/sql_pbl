from typing import Dict, List, Any, Optional
import sql_compiler as sc

class ColumnDef:
    def __init__(self, name: str, data_type: sc.TokenType):
        self.name = name
        self.type = data_type

class Table:
    def __init__(self, name: str, columns: List[ColumnDef], title: Optional[str] = None):
        self.name = name
        self.title = title if title else name
        self.columns = columns
        self.rows = []
        
    def add_row(self, values: List[Any]) -> bool:
        if len(values) != len(self.columns):
            print(f"Error: Column count mismatch. Expected {len(self.columns)}, got {len(values)}")
            return False
        for i, value in enumerate(values):
            if not self._validate_type(value, self.columns[i].type):
                print(f"Error: Type mismatch for column '{self.columns[i].name}'. Expected {self.columns[i].type}, got {type(value)}")
                return False
        self.rows.append(values)
        return True
    
    def _validate_type(self, value: Any, expected_type: sc.TokenType) -> bool:
        if value is None:
            return True
        if expected_type == sc.TokenType.INT:
            return isinstance(value, int)
        elif expected_type == sc.TokenType.FLOAT:
            return isinstance(value, (int, float))
        elif expected_type == sc.TokenType.TEXT:
            return isinstance(value, str)
        elif expected_type == sc.TokenType.DATE:
            return isinstance(value, str)
        return False
    
    def get_column_index(self, column_name: str) -> int:
        for i, col in enumerate(self.columns):
            if col.name.lower() == column_name.lower():
                return i
        return -1
    
    def print_table(self, columns: Optional[List[int]] = None) -> None:
        print(f"\nTable: {self.title}\n")
        if not columns:
            columns = list(range(len(self.columns)))
        header = [self.columns[i].name for i in columns]
        print(" | ".join(header))
        print("-" * (sum(len(h) for h in header) + 3 * (len(header) - 1)))
        for row in self.rows:
            row_data = ["NULL" if row[i] is None else str(row[i]) for i in columns]
            print(" | ".join(row_data))

class Database:
    def __init__(self):
        self.tables: Dict[str, Table] = {}
    
    def create_table(self, name: str, columns: List[ColumnDef], title: Optional[str] = None) -> bool:
        if name.lower() in self.tables:
            print(f"Error: Table '{name}' already exists")
            return False
        self.tables[name.lower()] = Table(name, columns, title)
        return True
    
    def drop_table(self, name: str) -> bool:
        if name.lower() not in self.tables:
            print(f"Error: Table '{name}' does not exist")
            return False
        del self.tables[name.lower()]
        return True
    
    def get_table(self, name: str) -> Optional[Table]:
        return self.tables.get(name.lower())
    
    def execute_query(self, ast: sc.ASTNode) -> bool:
        if ast.type == sc.NodeType.SELECT_STMT:
            return self._execute_select(ast)
        elif ast.type == sc.NodeType.INSERT_STMT:
            return self._execute_insert(ast)
        elif ast.type == sc.NodeType.UPDATE_STMT:
            return self._execute_update(ast)
        elif ast.type == sc.NodeType.DELETE_STMT:
            return self._execute_delete(ast)
        elif ast.type == sc.NodeType.CREATE_STMT:
            return self._execute_create(ast)
        elif ast.type == sc.NodeType.DROP_STMT:
            return self._execute_drop(ast)
        else:
            print(f"Error: Unsupported query type: {ast.type}")
            return False

    def _execute_select(self, ast: sc.ASTNode) -> bool:
        if not ast.data.get('tables', []):
            print("Error: No table specified in SELECT statement")
            return False
        table_node = ast.data['tables'][0]  # Accessing first table in list
        table_name = table_node.data['name']
        table = self.get_table(table_name)
        if not table:
            print(f"Error: Table '{table_name}' not found")
            return False
        selected_columns = []
        if ast.data['columns'][0].data['name'] == '*':
            selected_columns = list(range(len(table.columns)))
        else:
            for col_node in ast.data['columns']:
                col_name = col_node.data['name']
                col_idx = table.get_column_index(col_name)
                if col_idx == -1:
                    print(f"Error: Column '{col_name}' not found in table '{table_name}'")
                    return False
                selected_columns.append(col_idx)
        filtered_rows = []
        for row in table.rows:
            if not ast.data.get('where_clause') or self._evaluate_condition(ast.data['where_clause'], table, row):
                filtered_rows.append(row)
        temp_table = Table(table.name, table.columns, title=table.title)
        temp_table.rows = filtered_rows
        temp_table.print_table(selected_columns)
        print(f"\n{len(filtered_rows)} row(s) selected")
        return True

    def _execute_insert(self, ast: sc.ASTNode) -> bool:
        table_name = ast.data['table'].data['name']
        table = self.get_table(table_name)
        if not table:
            print(f"Error: Table '{table_name}' not found")
            return False
        if ast.data['columns']:
            column_indices = []
            for col_node in ast.data['columns']:
                col_name = col_node.data['name']
                col_idx = table.get_column_index(col_name)
                if col_idx == -1:
                    print(f"Error: Column '{col_name}' not found in table '{table_name}'")
                    return False
                column_indices.append(col_idx)
            values = [None] * len(table.columns)
            for i, col_idx in enumerate(column_indices):
                if i < len(ast.data['values']):
                    values[col_idx] = self._evaluate_expression(ast.data['values'][i])
            if not table.add_row(values):
                return False
        else:
            values = [self._evaluate_expression(expr) for expr in ast.data['values']]
            if not table.add_row(values):
                return False
        print("1 row inserted")
        return True

    def _execute_update(self, ast: sc.ASTNode) -> bool:
        table_name = ast.data['table'].data['name']
        table = self.get_table(table_name)
        if not table:
            print(f"Error: Table '{table_name}' not found")
            return False
        set_clauses = []
        for set_node in ast.data['set_clauses']:
            col_name = set_node.data['left'].data['name']
            col_idx = table.get_column_index(col_name)
            if col_idx == -1:
                print(f"Error: Column '{col_name}' not found in table '{table_name}'")
                return False
            value = self._evaluate_expression(set_node.data['right'])
            set_clauses.append((col_idx, value))
        rows_updated = 0
        for row in table.rows:
            if not ast.data.get('where_clause') or self._evaluate_condition(ast.data['where_clause'], table, row):
                for col_idx, value in set_clauses:
                    row[col_idx] = value
                rows_updated += 1
        print(f"{rows_updated} row(s) updated")
        return True

    def _execute_delete(self, ast: sc.ASTNode) -> bool:
        table_name = ast.data['table'].data['name']
        table = self.get_table(table_name)
        if not table:
            print(f"Error: Table '{table_name}' not found")
            return False
        rows_to_keep = []
        rows_deleted = 0
        for row in table.rows:
            if ast.data.get('where_clause') and not self._evaluate_condition(ast.data['where_clause'], table, row):
                rows_to_keep.append(row)
            else:
                rows_deleted += 1
        table.rows = rows_to_keep
        print(f"{rows_deleted} row(s) deleted")
        return True

    def _execute_create(self, ast: sc.ASTNode) -> bool:
        table_name = ast.data['table'].data['name']
        columns = []
        for col_node in ast.data['columns']:
            col_name = col_node.data['name']
            col_type = col_node.data['data_type']
            columns.append(ColumnDef(col_name, col_type))
        title = ast.data.get('title')
        if self.create_table(table_name, columns, title=title):
            print(f"Table '{table_name}' created")
            return True
        return False

    def _execute_drop(self, ast: sc.ASTNode) -> bool:
        table_name = ast.data['table'].data['name']
        if self.drop_table(table_name):
            print(f"Table '{table_name}' dropped")
            return True
        return False

    def _evaluate_condition(self, condition: sc.ASTNode, table: Table, row: List[Any]) -> bool:
        if condition.type == sc.NodeType.CONDITION:
            if 'operator' in condition.data and condition.data['operator'] == sc.TokenType.AND:
                return (self._evaluate_condition(condition.data['left'], table, row) and 
                        self._evaluate_condition(condition.data['right'], table, row))
            elif 'operator' in condition.data and condition.data['operator'] == sc.TokenType.OR:
                return (self._evaluate_condition(condition.data['left'], table, row) or 
                        self._evaluate_condition(condition.data['right'], table, row))
            elif 'operator' in condition.data and condition.data['operator'] == sc.TokenType.NOT:
                return not self._evaluate_condition(condition.data['right'], table, row)
            elif 'operator' in condition.data:
                left_value = self._evaluate_expression(condition.data['left'], table, row)
                right_value = self._evaluate_expression(condition.data['right'], table, row)
                op = condition.data['operator']
                if op == sc.TokenType.EQUALS: return left_value == right_value
                if op == sc.TokenType.NOT_EQUALS: return left_value != right_value
                if op == sc.TokenType.GREATER: return left_value > right_value
                if op == sc.TokenType.LESS: return left_value < right_value
                if op == sc.TokenType.GREATER_EQUALS: return left_value >= right_value
                if op == sc.TokenType.LESS_EQUALS: return left_value <= right_value
                print(f"Error: Unsupported operator: {op}")
                return False
        return bool(self._evaluate_expression(condition, table, row))

    def _evaluate_expression(self, expr: sc.ASTNode, table: Optional[Table] = None, row: Optional[List[Any]] = None) -> Any:
        if expr.type == sc.NodeType.IDENTIFIER:
            if table and row:
                col_idx = table.get_column_index(expr.data['name'])
                if col_idx != -1:
                    return row[col_idx]
            return expr.data['name']
        elif expr.type == sc.NodeType.LITERAL:
            return expr.data['value']
        elif expr.type == sc.NodeType.EXPRESSION:
            left_value = self._evaluate_expression(expr.data['left'], table, row)
            if expr.data['operator'] == sc.TokenType.DOT:
                return left_value + "." + self._evaluate_expression(expr.data['right'], table, row)
            right_value = self._evaluate_expression(expr.data['right'], table, row)
            op = expr.data['operator']
            if op == sc.TokenType.PLUS: return left_value + right_value
            if op == sc.TokenType.MINUS: return left_value - right_value
            if op == sc.TokenType.ASTERISK: return left_value * right_value
            if op == sc.TokenType.DIVIDE: return left_value / right_value
            print(f"Error: Unsupported operator: {op}")
            return None
        else:
            print(f"Error: Unsupported expression type: {expr.type}")
            return None
