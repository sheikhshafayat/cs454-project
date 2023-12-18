#!/bin/bash

# Define an array of target files
target_files=(
"ex/example1.py"
"ex/example2.py"
"ex/example3.py"
"ex/example4.py"
"ex/example5.py"
"ex/example6.py"
)  # Add your target files here

# Loop through each file and run the Python script
for file in "${target_files[@]}"; do
    echo "Running script for $file..."
    python sbst_all_inputs.py "$file" "False" "False"  # Replace 'your_python_script.py' with your actual Python script
done