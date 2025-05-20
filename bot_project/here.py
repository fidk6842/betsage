import os

def show_files_and_folders(directory, indent=0):
    try:
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            print(' ' * indent + '|-- ' + item)  # Tree structure
            if os.path.isdir(item_path):
                show_files_and_folders(item_path, indent + 4)  # Recursively go deeper
    except PermissionError:
        print(' ' * indent + '|-- [Permission Denied]')

# Example usage
directory_path = input("Enter the path of the directory: ")
print(f"\nShowing contents of: {directory_path}\n")
show_files_and_folders(directory_path)
