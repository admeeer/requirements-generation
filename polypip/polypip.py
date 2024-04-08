import argparse
import os
import re
from collections import defaultdict
import ast
import logging

def find_python_files(path, recursion=True):
    if recursion:
        
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                if filename.endswith('.py') or filename.endswith('.pyw'):
                    yield os.path.join(dirpath, filename)
    else:
        # os.listdir() returns both files and directories, hence the os.path.isfile check
        for filename in os.listdir(path):
            abs_path = os.path.join(path, filename)
            if os.path.isfile(abs_path) and (filename.endswith('.py') or filename.endswith('.pyw')):
                yield abs_path


# Changed to incorporate AST parsing. Parsing the AST is more reliable than using regex. In addition if an import is there and not commented out, it will be picked up by the AST parser.
def get_imports_from_file(path):
    
    with open(path, 'r', encoding='utf-8') as file:
        code = file.read()

    tree = ast.parse(code)

    all_imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            all_imports.extend([(name.name, name.asname) for name in node.names])
        elif isinstance(node, ast.ImportFrom):
            all_imports.extend([(node.module, name.asname) for name in node.names])

    if not all_imports:
        logging.warning(f"No imports found in {path}")

    return all_imports

def generate_requirements_file(path, imports):
    with open(path, 'w', encoding='utf-8') as req_file:
        for package in sorted(imports.keys()):
            req_file.write(f"{package}\n")

def gather_imports(files):
    imports = defaultdict(int)
    for file_path in files:
        for imp in get_imports_from_file(file_path):
            package = imp[0] or imp[1]
            imports[package] += 1
    return imports

def normalize_imports(imports):
    normalized_imports = defaultdict(int)
    for package, count in imports.items():
        normalized_package = package.split('.')[0]
        normalized_imports[normalized_package] += count
    return normalized_imports

# The module should provide an option for the user to input a requirements file and parse the 
#dependencies in that file. If a dependency is detected that is also inside the input file that has a 
# version specified, then the detected dependency is set to that version instead.

def driver(args):
    
    input_path = args.path

    if input_path is None:
        input_path = os.path.abspath(os.curdir)

    if os.path.isfile(input_path):
        
        if args.shallow:
            logging.info('used --shallow but input is a single file. ignoring.')
        
        files = [input_path]
        
        save_path = os.path.join(os.path.dirname(input_path), 'requirements.txt')

    else:

        files = find_python_files(path=input_path, recursion=args.shallow)

        save_path = os.path.join(input_path, 'requirements.txt')

    if not args.overwrite and os.path.exists(save_path):
        print('requirements.txt already exists. Use --o or --overwrite to overwrite.')
        return
    
    imports = gather_imports(files)
    normalized_imports = normalize_imports(imports)
    generate_requirements_file(save_path, normalized_imports)

def main():
    
    parser = argparse.ArgumentParser(prog='polypip')

    parser.add_argument('--path', '--p', help='path to the directory or file to scan for imports')
    parser.add_argument('--reference', '--r', help='path to a requirements.txt file to reference versions from')
    parser.add_argument('--overwrite', '--o', action='store_true', help='overwrite requirements.txt if it already exists')
    parser.add_argument('--shallow', '--s', action='store_false', help='do not search recursively')

    group = parser.add_mutually_exclusive_group()

    group.add_argument('--quiet', action='store_true', help='enable quiet mode')
    group.add_argument('--verbose', action='store_true', help='enable verbose mode')

    args = parser.parse_args()

    log_level = logging.INFO

    if args.quiet:
        log_level = logging.WARNING
    elif args.verbose:
        log_level = logging.DEBUG

    logging.basicConfig(level=log_level, format='%(levelname)s: %(message)s')

    driver(args)

if __name__ == "__main__":
    main()