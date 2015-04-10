#!/usr/bin/env python2

import sys


# possible results returned when a test is queried against the manifest
ABSENT      = 'ABSENT'
PASS        = 'PASS'
XFAIL       = 'XFAIL'
UNSUPPORTED = 'UNSUPPORTED'

# Values to represent 'wildcard' entries in the manifest for different
# parameters
WILDCARD_NAME    = ''
WILDCARD_FLAGS   = ''
WILDCARD_SUBTEST = ''
WILDCARD_LINE    = ''


def read_manifest(filename, manifest):
    manifest_file = None
    try:
        manifest_file = open(filename, 'r')
    except IOError:
        print >> sys.stderr, "error: Could not open override manifest (", filename, ")"
        return False
        
    success = True

    # iterate through every line in the file
    for line in manifest_file:
        orig_line = str(line)

        # ignore comment fields and empty lines
        if parse_comment(line):
            continue
        if not line.lstrip():
            continue

        # parse parameters
        result, line = parse_result(line)
        if not result:
            success = False
            break

        test_name, line = parse_field(line, WILDCARD_NAME)
        flags, line     = parse_field(line, WILDCARD_FLAGS)
        subtest, line   = parse_field(line, WILDCARD_SUBTEST)
        line_num, line  = parse_field(line, WILDCARD_LINE)

        if (test_name is None) or (flags is None) or (subtest is None) or (line_num is None):
            print >> sys.stderr, "warning: Failed to parse field of manifest entry (string: ", orig_line, ")"
            success = False
            continue

        # add the entry to the manifest
        manifest[(test_name, flags, subtest, line_num)] = result

    manifest_file.close()

    if not success:
        print >> sys.stderr, "error: failed to parse manifest entry"
    return success


def parse_comment(line):
    line = line.lstrip()
    if line:
        return line[0] == '#'
    else:
        return False


def parse_result(line):
    line = line.lstrip()
    line = line.split(':', 1)
    result = {
        'PASS'        : PASS,
        'XFAIL'       : XFAIL,
        'UNSUPPORTED' : UNSUPPORTED
    }.get(line[0], None)

    if not result:
        print >> sys.stderr, "error: Invalid expected result (", line[0], ")"
        return None, None 

    if len(line) < 2:
        return result, ''
    else:
        return result, line[1]


def parse_field(line, default):
    line = line.lstrip()
    
    # empty line, use default
    if not line:
        return default, '' 

    # capture field
    if not line[0] == '[':
        # missing field, use default
        return default, line
    else:
        line = line[1:]

    # grab up to the next closing brace
    line = line.split(']', 1)
    if len(line) == 1:
        print >> sys.stderr, 'warning: Missing end of field \']\''
        return None, line

    field = line[0]
    line  = line[1]

    # Replace runs of whitespace with a single space, and strip leading and
    # trailing whitespace
    field = field.strip()
    field = ' '.join(field.split())

    # empty field means use the default
    if not field:
        return default, line
    return field, line


def query_manifest(line, manifest):
    # parse all of the fields which may make up the query
    test_name, line = parse_field(line, WILDCARD_NAME)
    flags, line     = parse_field(line, WILDCARD_FLAGS)
    subtest, line   = parse_field(line, WILDCARD_SUBTEST)
    line_num, line  = parse_field(line, WILDCARD_LINE)

    # If any of the fields are None then they failed to parse
    if (test_name is None) or (flags is None) or (subtest is None) or (line_num is None):
        print >> sys.stderr, 'error: Failed to parse one or more fields'
        return ABSENT

    print "QUERY: ", test_name, flags, subtest, line_num
    
    # Look for the most specific entry in the manifest which covers this test.
    # The later parameters are considered less significant than the earlier

    # entries for this specific test
    res = manifest.get((test_name, flags, subtest, line_num), None)
    if res:
        return res

    # entry for same flags and subtest, but on any line
    res = manifest.get((test_name, flags, subtest, WILDCARD_LINE), None)
    if res:
        return res

    # entry for same flags and line, but any subtest
    res = manifest.get((test_name, flags, WILDCARD_SUBTEST, line_num), None)
    if res:
        return res

    # entry for same flags, but any subtest and any line
    res = manifest.get((test_name, flags, WILDCARD_SUBTEST, WILDCARD_LINE), None)
    if res:
        return res

    # any flags, but same subtest and line
    res = manifest.get((test_name, WILDCARD_FLAGS, subtest, line_num), None)
    if res:
        return res

    # any flags and any line number, but same subtest
    res = manifest.get((test_name, WILDCARD_FLAGS, subtest, WILDCARD_LINE), None)
    if res:
        return res

    # any flags and any subtest, but same line
    res = manifest.get((test_name, WILDCARD_FLAGS, WILDCARD_SUBTEST, line_num), None)
    if res:
        return res

    # any flags subtest and line
    res = manifest.get((test_name, WILDCARD_FLAGS, WILDCARD_SUBTEST, WILDCARD_LINE), None)
    if res:
        return res

    # Test is not present in the manifest
    return ABSENT


def main():
    if len(sys.argv) < 2:
        print >> sys.stderr, "error: No override manifest provided"
        print "ERROR"
        exit(-1)

    # read in the manifest file
    manifest_filename = sys.argv[1]
    manifest = {}

    res = read_manifest(manifest_filename, manifest)
    if res == False:
        print >> sys.stderr, "error: Could not read override manifest (", manifest_filename, ")"
        print "ERROR"
        exit(-1)

    # Ready to respond to queries
    print "READY"

    # Continually read queries from standard input
    while True:
        line = sys.stdin.readline()
        
        # finish when given an empty line
        if not line:
            break

        # handle the query
        res = query_manifest(line, manifest)
        if not res:
            print >> sys.stderr, "warning: Failed when querying manifest (query: ", args, ")"
            res = ABSENT
        print res


if __name__ == '__main__':
    main()













def parse_test_name(line):
    line = line.lstrip()
    
    # empty or wildcard
    if not line:
        return WILDCARD_NAME, line
    elif line[0] == '*':
        return WILDCARD_NAME, line[1:]

    # take everything up to first flag or next wildcard (begins with hypen)
    # TODO: needs better handling
    line = line.split(' *', 1)
    if len(line) == 1:
        line = line[0].split(' -', 1)
        if len(line) != 1:
            line[1] = '-' + line[1]
    else:
        line[1] = '*' + line[1]
        
    test_name = line[0].rstrip()
    if len(line) == 1:
        return test_name, ''
    else:
        return test_name, line[1]


def parse_flags(line):
    line = line.lstrip()

    # empty line or wildcard
    if not line:
        return WILDCARD_FLAGS, line
    elif line[0] == '*':
        return WILDCARD_FLAGS, line[1:]

    flags = []
    while True:
        line = line.lstrip()

        if line:
            # split flags on whitespace
            line = line.split(None, 1)

            flags.append(line[0])
            if len(line) == 1:
                line = ''
            else:
                line = line[1]
        else:
            break

    if flags:
        return tuple(flags), line
    else:
        return WILDCARD_FLAGS, line


