import argparse
from zettelgeist import zdb

parser = zdb.get_argparse()

for field in zdb.ZettelSQLFields:
    parser.add_argument('--find-%s' %
                        field, help='search the Zettel %s field' % field)
    parser.add_argument('--exclude-%s' %
                        field, help='search the Zettel %s field' % field)
    parser.add_argument('--show-%s' %
                        field, action='store_const', const=True, default=False)

parser.add_argument('--count', action='store_const', const=True,
                    default=False, help="Show number of Zettels matching this search")

def main():
	args = parser.parse_args()

	argsd = vars(args)
	query = []
	for field in zdb.ZettelSQLFields:
	    exclude_field = 'exclude_' + field
	    include_field = 'find_' + field
	    if exclude_field in argsd:
	        entry = argsd.get(exclude_field)
	        if entry:
	            query.append((field, '-', entry))
	    if include_field in argsd:
	        entry = argsd.get(include_field)
	        if entry:
	            query.append((field, '', entry))

	db = zdb.get(args.database)
	gen = db.fts_search(query)

	search_count = 0
	for row in gen:
	    search_count = search_count + 1
	    printed_something = False
	    for field in row.keys():
	        show_field = "show_" + field
	        if argsd.get(show_field, None):
	            if len(row[field]) > 0:
	                print("%s:" % field)
	                print(row[field])
	                print()
	                printed_something = True

	    if printed_something:
	        print("-" * 40)
	        print()

	if args.count:
	    print("%d Zettels matched search" % search_count)

if __name__ == '__main__':
	main()