import sys
import argparse
import yaml
from . import zdb, zettel, zquery


def get_argparse():
    parser = zdb.get_argparse()
    parser.add_argument('--use-index', action='store_const',
                        const=True, default=False)

    for field in zdb.ZettelSQLFields:
        # parser.add_argument('--find-%s' %
        #                    field, help='search the Zettel %s field' % field)
        # parser.add_argument('--exclude-%s' %
        #                    field, help='search the Zettel %s field' % field)
        parser.add_argument('--show-%s' % field,
            action='store_const', const=True, default=False,
            help="include field <%s> in output" % field)

        parser.add_argument('--context-%s' % field,
            type=int, default=32,
            help="Set context width for field %s (default 32)" % field)

    parser.add_argument(
        '--count', action='store_const', const=True, default=False,
        help="Show number of Zettels matching this search")

    parser.add_argument(
        '--prompt', action='store_const', const=True, default=False,
        help="enter query interactively (overrides --input))")

    parser.add_argument(
        '--query',
        help="load query from file", default=None)

    parser.add_argument(
        '--save-query',
        help="save source query to file", default=None)

    parser.add_argument(
        '--trace-sql',
        help="log all SQL statements used to file", default=None)

    parser.add_argument(
        '--save-sql',
        help="save compiled SQL to file (for developers only)", default=None)
    return parser

def write_data(filename, mode, comment, statement):
    if not filename:
        return
    with open(filename, mode) as outfile:
        outfile.write("\n".join([comment, statement]) + "\n\n")

def counter():
    i = 0
    while True:
        yield i
        i = i + 1

def main():
    parser = get_argparse()
    args = parser.parse_args()

    argsd = vars(args)

    if args.prompt:
        input_line = input("zquery> ")

    elif args.query:
        with open(args.query) as infile:
            input_line = infile.read()
    else:
        print("No query to process: Use --prompt or --query")
        return

    (ast2, semantics2) = zquery.compile2(input_line)
    db = zdb.get(args.database)
    gen = None
    for statement in semantics2.create_sql(ast2):
        write_data(args.trace_sql, "a", "", statement)
        gen = db.fts_query(statement)
        for g in gen: pass

    select_sql = semantics2.select_sql()
    search_result_generator = db.fts_query(select_sql)

    write_data(args.trace_sql, "a", "# query match", select_sql)
    write_data(args.save_query, "w", "", input_line)
    write_data(args.save_sql, "w", "", ast2)
    write_data(args.trace_sql, "a", "# saved SQL query", ast2)

    search_counter = counter()
    results_counter = counter()

    search_count = next(search_counter)
    results_printed = next(results_counter)

    search_result_generator = db.fts_query(select_sql)
    for search_result in list(search_result_generator):
        docid = search_result['docid']
        print(">>> Processing", docid)
        bound_query = "SELECT *,docid from zettels where docid = %(docid)s" % vars()
        write_data(args.trace_sql, "a", "# finding zettels by docid", bound_query)

        search_details_generator = db.fts_query(bound_query)
        try:
            row = next(search_details_generator)
        except:
            print("Unexpected end of iteration")

        if results_printed:
            print("-" * 3)

        z = None
        if not args.use_index:
            loader = zettel.ZettelLoader(row['filename'])
            zettels = loader.getZettels()
            z = next(zettels)

        for field in zettel.ZettelFields:
            show_field = "show_" + field
            context_field = "context_" + field
            if argsd.get(show_field, None):
                for query in semantics2.get_field_query_sql(field, argsd[context_field], docid):
                    field_query_generator = db.fts_query(query)
                    write_data(args.trace_sql, "a", "", query)
                    for result in field_query_generator:
                        if result[field]:
                            if z:
                                print(z.get_yaml([field]))
                            else:
                                print(zettel.dict_as_yaml(
                                    {field: result[field]}))
                            results_printed = next(results_counter)

        # TODO: Allow filename to be kept in the Zettel. Should be possible but we would just never save it.
        # Would like to eliminate special case code like the following to eliminate duplication.

        if argsd.get("show_filename"):
            for query in semantics2.get_field_query_sql('filename', 32768, docid):
                write_data(args.trace_sql, "a", "", query)
                field_query_generator = db.fts_query(query)

                for result in field_query_generator:
                    print(zettel.dict_as_yaml(
                        {"filename": result["filename"]}))
                    results_printed = next(results_counter)

        search_count = next(search_counter)

    if args.count:
        if results_printed:
            print("-" * 3)
        doc = {'count': search_count, 'query': input_line}
        print(zettel.dict_as_yaml(doc))

if __name__ == '__main__':
    main()
