#!/usr/bin/python3
import sys
import subprocess
import re
import os

def run_namei(path):
    try:
        abs_path = os.path.abspath(path)
        result = subprocess.run(['namei', '-l', abs_path], capture_output=True, text=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running namei: {e}", file=sys.stderr)
        return None
    except FileNotFoundError:
        print("Error: 'namei' command not found. Please ensure it's installed.", file=sys.stderr)
        return None

def parse_namei_output(output):
    entries = []
    lines = output.strip().split('\n')
    
    for line in lines:
        match = re.match(r'([fdl-]):\s+(.+)', line)
        if match:
            entries.append({'type': match.group(1), 'path': match.group(2)})
        else:
            match = re.match(r'([dl-])([rwx-]{9})\s+(\S+)\s+(\S+)\s+(.+)', line)
            if match:
                entry = {
                    'type': match.group(1),
                    'permissions': match.group(2),
                    'owner': match.group(3),
                    'group': match.group(4),
                    'name': match.group(5)
                }
                entries.append(entry)
    
    return entries

def green_text(text):
    return f"\033[32m{text}\033[0m"

def red_text(text):
    return f"\033[31m{text}\033[0m"

def get_user_groups(username):
    try:
        result = subprocess.run(['groups', username], capture_output=True, text=True, check=True)
        return result.stdout.strip().split()[1:]  # Skip the username at index 0
    except subprocess.CalledProcessError as e:
        print(f"Error getting user groups: {e}", file=sys.stderr)
        return []

def color_permissions(perms):
    if 'r' not in perms or 'x' not in perms:
        return red_text(perms)
    return green_text(perms)

def has_permission_based_on_type(type, perms):
    if type not in '-d':
        print(f"Unsupported file type ${type}, exiting ...")
        sys.exit(2)
    return 'r' in perms or (type == 'd' and 'x' in perms)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Why no permission: \nutiliy script to help you find out why a certain user does not have r/x access to a folder/file")
        print(f"\tUsage: python ynp.py <username> <path>", file=sys.stderr)
        sys.exit(1)
    
    username = sys.argv[1]
    path = os.path.abspath(sys.argv[2])
    namei_output = run_namei(path)
    
    if namei_output:
        parsed_entries = parse_namei_output(namei_output)
        user_groups = get_user_groups(username)
        for entry in parsed_entries:
            if 'path' in entry:
                print(f"{entry['type']}: {entry['path']}")
            else:
                type = entry['type']
                user_perms = entry['permissions'][:3]
                group_perms = entry['permissions'][3:6]
                other_perms = entry['permissions'][6:]

                min_access = 'r--' if type == '-' else 'r-x'
                
                hint = ''
                if username == entry['owner']:
                    if has_permission_based_on_type(type, user_perms):
                        user_perms = green_text(user_perms)
                    else:
                        user_perms = red_text(user_perms)
                        hint = f'# User does not have {min_access} access'
                elif entry['group'] in user_groups:
                    if has_permission_based_on_type(type, group_perms):
                        group_perms = green_text(group_perms)
                    else:
                        group_perms = red_text(group_perms)
                        hint = f'# User belongs to a group ({entry['group']}) with no {min_access} access'
                else:
                    if has_permission_based_on_type(type, other_perms):
                        other_perms = green_text(other_perms)
                    else:
                        other_perms = red_text(other_perms)
                        hint = f'# Other users do not have {min_access} access'
                
                print(f"{entry['type']}{user_perms}{group_perms}{other_perms}  {entry['owner']:<15} {entry['group']:<15} {entry['name']:15} {red_text(hint)}")
