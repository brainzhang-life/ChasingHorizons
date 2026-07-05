import os

def format_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.split('\n')
    new_lines = []
    i = 0
    n = len(lines)
    modified = False
    
    while i < n:
        line = lines[i]
        is_table_start = False
        if i + 1 < n:
            next_line = lines[i+1]
            stripped_line = line.strip()
            stripped_next = next_line.strip()
            
            if stripped_line.startswith('|') and stripped_line.endswith('|'):
                if stripped_next.startswith('|') and stripped_next.endswith('|'):
                    # Check if next line is a separator row
                    if all(c in '|:- \t' for c in stripped_next) and '-' in stripped_next:
                        is_table_start = True
        
        if is_table_start:
            # Check if we need to insert a blank line before the table
            if new_lines and new_lines[-1].strip() != '':
                new_lines.append('')
                modified = True
            
            # Process table lines
            while i < n and lines[i].strip().startswith('|') and lines[i].strip().endswith('|'):
                formatted_line = '    ' + lines[i].strip()
                if lines[i] != formatted_line:
                    modified = True
                new_lines.append(formatted_line)
                i += 1
        else:
            new_lines.append(line)
            i += 1
            
    if modified:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines))
        print(f"Formatted tables in {file_path}")
    else:
        print(f"No changes needed for {file_path}")

def main():
    docs_dir = 'docs'
    for root, dirs, files in os.walk(docs_dir):
        for file in files:
            if file.endswith('.md'):
                file_path = os.path.join(root, file)
                format_file(file_path)

if __name__ == '__main__':
    main()
