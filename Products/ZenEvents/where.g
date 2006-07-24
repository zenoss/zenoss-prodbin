 parser WhereClause:
    ignore:    "[ \r\t\n]+"
    token END: "$"
    token NUM: "[0-9]+"
    token VAR: "[a-zA-Z0-9_]+"
    token BIN: ">=|<=|==|=|<|>|!=|<>"
    token STR: r'"([^\\"]+|\\.)*"'
    token STR2: r"'([^\\']+|\\.)*'"

    rule goal:    andexp END         {{ return andexp }}

    rule andexp:  orexp              {{ e = orexp }}
                  ( "and" orexp      {{ e = ('and', e, orexp) }}
                  )*                 {{ return e }}

    rule orexp:   binary             {{ e = binary }}
                  ( "or" binary      {{ e = ('or', e, binary) }}
                  )*                 {{ return e }}

    rule binary:  term               {{ e = term }}
                  ( BIN term         {{ e = (BIN, e, term) }}
                    | 'like' term    {{ e = ('like', e, term) }}
                    | 'not' 'like' term
                                     {{ e = ('not like', e, term) }}
                  )*                 {{ return e }}

    rule term:    NUM                {{ return int(NUM) }}
                  | VAR              {{ return VAR }}
                  | STR              {{ return STR }}
                  | STR2             {{ return STR2 }}
                  | "\\(" andexp "\\)" {{ return andexp }}
