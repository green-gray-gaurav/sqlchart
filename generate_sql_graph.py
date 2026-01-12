import sqlglot
from sqlglot import exp
from graphviz import Digraph
import textwrap
from copy import deepcopy
import re
import argparse




#------------------------------taking the arguments-----------------------
parser = argparse.ArgumentParser(
    description="Generate SELECT-subquery graph from SQL"
)

parser.add_argument(
    "--sql",
    required=True,
    help="Path to SQL file"
)

parser.add_argument(
    "--out",
    default="sql_select_graph",
    help="Output file name (without extension)"
)

parser.add_argument(
    "--format",
    default="svg",
    choices=["svg", "png", "pdf"],
    help="Graph output format"
)

args = parser.parse_args()

sql_file = args.sql
output_name = args.out
output_format = args.format




dot = Digraph(comment='SQL SELECT Graph' , format = output_format)


DML_TYPES = (exp.Insert, exp.Update, exp.Delete)

with open(f"{sql_file}.sql") as f:
    sql_str = f.read()


parsed = sqlglot.parse_one(sql_str)

def build_select_nodes(node, parent_id=None, nodes=None, node_id_counter=None , in_cte=False , cte_name=None):
    """
    Recursively extract SELECT statements as nodes with parent-child info.
    Each node is a dict: {id, sql, parent_id, level}
    """
    if nodes is None:
        nodes = []
    if node_id_counter is None:
        node_id_counter = [1]  # mutable counter
    # Detect entering a CTE

    if isinstance(node, exp.CTE):
        in_cte = True
        if node.alias:
            cte_name = node.alias
    
        # -------- DML NODE --------
    if isinstance(node, DML_TYPES):
        node_id = node_id_counter[0]
        nodes.append({
            "id": node_id,
            "node": node,
            "node_type": type(node).__name__,  # Insert / Update / Delete
            "parent_id": parent_id,
            "is_cte": False,
            "cte_name": None
        })
        node_id_counter[0] += 1
        parent_id_for_children = node_id

    elif isinstance(node, exp.Select):

        cte_type = None

        # Detect recursive CTE member
        if in_cte and isinstance(node.parent, exp.Union):
            if node is node.parent.left:
                cte_type = "anchor"
            elif node is node.parent.right:
                cte_type = "recursive"


        node_id = node_id_counter[0]
        nodes.append({
            "id": node_id,
            "node": node,
            "node_type": "Select",
            "parent_id": parent_id,
            "is_cte": in_cte,
            "cte_name" : cte_name ,
            "cte_member": cte_type ,
            'clauses': extract_select_clauses(node)
        })


        in_cte = False
        node_id_counter[0] += 1
        parent_id_for_children = node_id
    else:
        parent_id_for_children = parent_id

    for child in node.args.values():
        if isinstance(child, list):
            for c in child:
                if isinstance(c, exp.Expression):
                    build_select_nodes(c, parent_id_for_children, nodes, node_id_counter , in_cte=in_cte , cte_name=cte_name)
        elif isinstance(child, exp.Expression):
            build_select_nodes(child, parent_id_for_children, nodes, node_id_counter , in_cte=in_cte , cte_name=cte_name)

    return nodes


def get_sql_without_children(node , node_id_map):
    """
    Return SQL for a SELECT node with child SELECTs replaced by placeholders.
    """
    # node_copy = deepcopy(node_)  # make a copy to not mutate original

    def replace_children(node):
        # print(id(node))
        for k, child in node.args.items():
            if isinstance(child, list):
                for i, c in enumerate(child):
                    if isinstance(c, exp.Select):
                        child_id = node_id_map.get(c, '?')  # use id(c) here
                        child[i] = exp.Identifier(this=f"$subquery_{child_id}$")
                    elif isinstance(c, exp.Expression):
                        replace_children(c)

            elif isinstance(child, exp.Select):
                child_id = node_id_map.get(child, '?')  # use id(child) here
                node.set(k, exp.Identifier(this=f"$subquery_{child_id}$"))
            elif isinstance(child, exp.Expression):
                replace_children(child)

    replace_children(node)
    return node.sql()


def extract_select_clauses(select_node):
    clause_map = {
        "SELECT": select_node.args.get("expressions"),
        "FROM": select_node.args.get("from_"),
        "WHERE": select_node.args.get("where"),
        "GROUP BY": select_node.args.get("group"),
        "ORDER BY": select_node.args.get("order"),
    }

    clauses = {}
    for name, expr in clause_map.items():
        if expr:
            if isinstance(expr, list):
                clauses[name] = ", ".join(e.sql() for e in expr)
            else:
                clauses[name] = expr.sql()
    return clauses




d_nodes = build_select_nodes(parsed)

node_id_map = {id(n['node']): n['id'] for n in d_nodes}


copied_nodes = deepcopy(d_nodes)
copied_node_id_map = {}

for original, copy_node in zip(d_nodes, copied_nodes):
    # copy_node['node'] is the deepcopy
    # original['id'] is the original ID
    copied_node_id_map[copy_node['node']] = original['id']



print(node_id_map)


nodes = []







for n in copied_nodes:



    # Only show parent’s own SQL, not embedded child SQL
    clean_sql = get_sql_without_children(n['node'] , copied_node_id_map)
    nodes.append({
        "id": n['id'],
        "node" : n['node'],
        "parent_id": n['parent_id'],
        "sql": clean_sql,
        "is_cte": n['is_cte'],
        "cte_name" : n['cte_name'] if n['is_cte'] else None
        ,"node_type": n['node_type'],
        "cte_member": n.get("cte_member" , "")
    })



# for n in nodes:
#     # 1. Clean the SQL and handle HTML escaping first
#     sql_clean = n['sql'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

#     #habdling cte nodes with different color
#     fill_map = {
#     "Select":  "#D6EAF8",  # soft sky blue – data read
#     "Insert":  "#D5F5E3",  # soft mint green – data write
#     "Update":  "#FCF3CF",  # warm pastel yellow – data change
#     "Delete":  "#FADBD8",  # soft rose – data removal
#     "CTE":     "#E8DAEF",  # light lavender – logical grouping
# }
#     fill = fill_map.get(n["node_type"], "gray")

#     fill = fill_map["CTE"] if n['is_cte'] else fill
#     cte_name = n['cte_name'] if n['is_cte'] else ""
   

#     # 2. Wrap the SQL at 50 chars
#     lines = textwrap.wrap(sql_clean, width=50)

#     wrapped_lines = []
#     for line in lines:
#         # 3. Style the subquery placeholders
#         # This replaces $subquery_10$ with Bold Red text
#         line = re.sub(
#             r'\$(subquery_\d+)\$', 
#             r'<B><FONT COLOR="red" POINT-SIZE="14">\1</FONT></B>', 
#             line
#         )
#         wrapped_lines.append(line)

#     cte_label = (
#     f"<FONT COLOR='red' POINT-SIZE='15'><B>CTE: {n['cte_name']}</B></FONT><BR ALIGN='CENTER'/>"
#     if n.get("cte_name")
#     else "" 
#     )

#     cte_member_label = ""
  
#     if n["cte_member"] == "anchor":
#         cte_member_label = (
#             "<FONT COLOR='#1E8449'><B>ANCHOR</B></FONT><BR ALIGN='CENTER'/>"
#         )
#     elif n["cte_member"] == "recursive":
#         cte_member_label = (
#             "<FONT COLOR='#1E8449'><B>RECURSIVE</B></FONT><BR ALIGN='CENTER'/>"
#         )
    

#     # 4. Use ALIGN="LEFT" in the join to keep SQL looking like code
#     # We add a title "Node #" at the top centered
#     header = f"<B>Node {n['id']} </B><BR ALIGN='CENTER'/>" + cte_label + cte_member_label
#     html_label = "<" + header + "<BR ALIGN='LEFT'/>".join(wrapped_lines) + "<BR ALIGN='LEFT'/>>"
    
#     dot.node(
#         str(n['id']),
#         label=html_label,
#         shape='box',
#         style='rounded,filled',
#         fillcolor=fill,
#         fontname='Courier' # Monospace font for SQL
#     )

#     # ---------- CLAUSE SUBNODES ----------
#     if n["node_type"] != "Select":
#         continue

#     clause_map = {
#         "SELECT": "expressions",
#         "FROM": "from",
#         "WHERE": "where",
#         "GROUP BY": "group",
#         "ORDER BY": "order",
#     }

#     clause_index = 0
#     for clause_name, arg_key in clause_map.items():
#         clause = n["node"].args.get(arg_key)
#         if not clause:
#             continue

#         clause_index += 1
#         clause_id = f"{n['id']}_{clause_index}"

#         if isinstance(clause, list):
#             clause_sql = ", ".join(c.sql() for c in clause)
#         else:
#             clause_sql = clause.sql()

#         clause_sql = (
#             clause_sql
#             .replace("&", "&amp;")
#             .replace("<", "&lt;")
#             .replace(">", "&gt;")
#         )

#         clause_sql = re.sub(
#             r'\$(subquery_\d+)\$',
#             r'<B><FONT COLOR="red">\1</FONT></B>',
#             clause_sql
#         )

#         lines = textwrap.wrap(clause_sql, width=50)
#         body = "<BR ALIGN='LEFT'/>".join(lines)

#         label = (
#             f"<B>{clause_name}</B>"
#             "<BR ALIGN='LEFT'/>"
#             f"{body}"
#         )

#         dot.node(
#             clause_id,
#             label=f"<{label}>",
#             shape="box",
#             style="rounded,filled",
#             fillcolor="#FDFEFE",
#             fontname="Courier"
#         )

#         dot.edge(str(n["id"]), clause_id)

def clause_body_sql(expr):
    # FROM / WHERE / GROUP / ORDER wrap the real expression in `.this`
    if hasattr(expr, "this") and expr.this:
        return expr.this.sql()
    return expr



for n in nodes:
    fill_map = {
        "Select":  "#D6EAF8",
        "Insert":  "#D5F5E3",
        "Update":  "#FCF3CF",
        "Delete":  "#FADBD8",
        "CTE":     "#E8DAEF",
    }

    fill = fill_map.get(n["node_type"], "gray")
    fill = fill_map["CTE"] if n["is_cte"] else fill

    # -------- Header labels --------
    cte_label = (
        f"<FONT COLOR='#ac8e72'><B>CTE: {n['cte_name']}</B></FONT><BR/>"
        if n.get("cte_name")
        else ""
    )

    cte_member_label = ""
    if n.get("cte_member") == "anchor":
        cte_member_label = "<FONT COLOR='#1E8449'><B>ANCHOR</B></FONT><BR/>"
    elif n.get("cte_member") == "recursive":
        cte_member_label = "<FONT COLOR='#1E8449'><B>RECURSIVE</B></FONT><BR/>"

    # -------- Clause rows (ONLY for SELECT) --------
    clause_rows = ""

    if n["node_type"] == "Select":
        clause_map = [
            ("SELECT", "expressions"),
            ("FROM", "from_"),
            ("WHERE", "where"),
            ("GROUP BY", "group"),
            ("ORDER BY", "order"),
        ]

        for title, key in clause_map:
            clause = n["node"].args.get(key)
            if not clause:
                continue

            if isinstance(clause, list):
                clause_sql = ", ".join(c.sql() for c in clause)
            else:
                clause = get_sql_without_children(clause , copied_node_id_map)
                clause_sql = clause_body_sql(clause)

            clause_sql = (
                clause_sql
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )

            wrapped_lines = textwrap.wrap(clause_sql, 60)

            wrapped = "<BR ALIGN='LEFT'/>".join(
                re.sub(
                    r'\$(subquery_\d+)\$',
                    r'<B><FONT COLOR="red">\1</FONT></B>',
                    line
                )
                for line in wrapped_lines
            )


            clause_rows += f"""
            <TR>
                <TD ALIGN="LEFT" VALIGN="TOP"><B>{title}</B></TD>
                <TD ALIGN="LEFT" VALIGN="TOP">{wrapped}</TD>
            </TR>
            """


    # -------- Non-SELECT SQL body --------
    non_select_rows = ""

    if n["node_type"] != "Select":
        sql_clean = (
            n["sql"]
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        wrapped = "<BR ALIGN='LEFT'/>".join(textwrap.wrap(sql_clean, 60))
        wrapped = re.sub(
                r'\$(subquery_\d+)\$',
                r'<B><FONT COLOR="red">\1</FONT></B>',
                wrapped
            )


        non_select_rows = f"""<TR><TD COLSPAN="2" ALIGN="LEFT" VALIGN="TOP">
                {wrapped}
            </TD></TR>"""



    rows = clause_rows if n["node_type"] == "Select" else non_select_rows



    html_label = f"""<
    <TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="5" MARGIN="0">
        <TR>
            <TD COLSPAN="2" ALIGN="CENTER" BGCOLOR="#cfe7e9">
                <B>Node {n['id']} ({n['node_type']})</B><BR/>
                {cte_label}
                {cte_member_label}
            </TD>
        </TR>
        {rows}
    </TABLE>
    >"""


    dot.node(
        str(n["id"]),
        label=html_label,
        shape="box",
        style="filled",
        fillcolor=fill,
        fontname="monospace",
        margin="0"
    )


for n in nodes:
    if n['parent_id'] is not None:
        dot.edge(str(n['parent_id']), str(n['id']) , label=" contains" , fontcolor="black")



# dot.attr(rankdir="TB")
dot.attr(fontname="JetBrains Mono")
# dot.attr('node', fontname="JetBrains Mono")
dot.render(f'{output_name}', cleanup=True , view = True)