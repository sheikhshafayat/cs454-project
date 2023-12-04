import coverage
import subprocess
import argparse
import subprocess
import re
import random
import os
import ast 
import json
from library import *

def collect_literals(node):
    literals = []
    if isinstance(node, (ast.Num, ast.Str, ast.List, ast.Tuple, ast.Constant)):
        literals.append(node)
    for child in ast.iter_child_nodes(node):
        literals.extend(collect_literals(child))
    literals = list(set(literals))  # Remove duplicates
    return literals

def parse_literal(node):
    if isinstance(node, ast.Num):
        return node.n
    elif isinstance(node, ast.Str):
        return node.s
    elif isinstance(node, (ast.List, ast.Tuple)):
        return [parse_literal(elem) for elem in node.elts]
    elif isinstance(node, ast.Constant):
        return node.value
    return None

def collect_inputs(node):
    literals = collect_literals(node)
    inputs = [parse_literal(literal) for literal in literals]
    inputs = [value for value in inputs if value is not None]
    return inputs

def parse_answer(text):
    try:
      match = re.search(r'(\{.*?\})', text)
      answer_text = match.group(1)
      final = json.loads(answer_text)['inputs']
      return final
    except Exception as e:
        return None
   
def extract_function_info(node):
    functions_info = []
    for item in node.body:
        if isinstance(item, ast.FunctionDef):
            function_name = item.name
            num_arguments = len(item.args.args)
            functions_info.append((function_name, num_arguments))
    return functions_info

# Modify fitness_function to accept different types of arguments
def fitness_function(script_path, function_name, arguments):
    # Convert arguments to string representation
    result = [repr(arg) for arg in arguments]
    target_module = os.path.basename(script_path).removesuffix(".py")
    second_part = ""
    for arg in arguments:
        #second_part += f"\t{target_module}.{function_name}({repr(arg)})\n"
        second_part += f"\t{target_module}.{function_name}{arg}\n"

    test_file_content = f'''
import {target_module}
def test_sample():
{second_part}
    '''.strip()

    test_file_name = os.path.join(os.path.dirname(script_path), "test_" + os.path.basename(script_path))
    with open(test_file_name, 'w') as f:
        f.write(test_file_content)

    run_command = ["coverage", "run", "-m", "pytest", test_file_name]
    subprocess.run(run_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    report_command = ["coverage", "report"]
    report_output = subprocess.run(report_command, text=True, capture_output=True)

    coverage_line = report_output.stdout.splitlines()[-1]
    coverage_percent_match = re.search(r'(\d+%)', coverage_line)
    if coverage_percent_match:
        coverage_percent = int(coverage_percent_match.group(1)[:-1])
        return coverage_percent, test_file_content
    else:
        raise ValueError("Failed to parse coverage percentage")

# Modify hill_climbing to work with different types of arguments
def hill_climbing(script_path, function_name, num_arguments, inputs_list, max_iterations=100):
    arg_list = []

    system_prompt_0 = f"""You are given a piece of code. Your job is to generate a
    test case that will maximize the code coverage of the test suite.
    Return your test case as a list of inputs to the function. The size of the list 
    is equal to the number of arguments of the function.

    Retun the test case within this  json format: {{"inputs": [arg1, arg2, ...]}}
    The code is given below within triple ticks.
    """

    system_prompt_1 = f"""You are given a piece of code and some already generated test cases as tuples. 
    However, those test cases reached a plateau in terms of code coverage.
    Your job is to generate one more test case that will maximize the code coverage of the test suite.

    Return your test case as a list of inputs to the function. The size of the list 
    is equal to the number of arguments of the function.

    Retun the test case within this  json format: {{"inputs": [arg1, arg2, ...]}}
    The code and current test cases are given below within triple ticks.
    """



    # gpt initialization
    # get the code
    with open(script_path, "r") as f:
        code = f.read()
    
    random_tuple = None 
    while random_tuple is None:
        random_tuple = get_gpt_response(code, system_prompt_0, model="gpt-3.5-turbo-1106")
        random_tuple = tuple(parse_answer(random_tuple))
    
    arg_list.append(random_tuple)
    print(f"Initial arguments: {arg_list}")

    current_fitness, _ = fitness_function(script_path, function_name, arg_list)
    print(f"Current fitness: {current_fitness}")

    it = 0
    up = 0
    while (it < max_iterations) and (current_fitness < 100):
        print(f"Iteration: {it}")
        # Generate a neighbor
        arg_list_2 = arg_list.copy()
        neighbor_index = random.randint(0, num_arguments - 1)
        tmp = list(arg_list_2[-1])
        #tmp[neighbor_index] = random.choice(inputs_list)
        tmp[neighbor_index] += random.randint(-5, 5)  # hyperparameter
        tmp = tuple(tmp)

        if it - up > 5:  # if stuck in a local optimum, make a jump
            # gpt jump
            prompt = f"Code:\n{code}\n\nCurrent Test Cases:\n{str(arg_list_2)}"
            tmp = None
            while tmp is None:
                tmp = get_gpt_response(prompt, system_prompt_1, model="gpt-3.5-turbo-1106")
                tmp = parse_answer(tmp)
                print(f"tmp: {tmp}")
                if tmp is None:
                    continue
                tmp = tuple(tmp)

            up = it
        arg_list_2.append(tmp)

        # Calculate the fitness after the change
        neighbor_fitness, _ = fitness_function(script_path, function_name, arg_list_2)

        if neighbor_fitness > current_fitness:
            arg_list = arg_list_2
            current_fitness = neighbor_fitness
            up = it
        it += 1

    final_fitness, final_test_file_content = fitness_function(script_path, function_name, arg_list)
    print(f"Final arguments: {arg_list}")
    print(f"Final fitness: {final_fitness}")
    return final_test_file_content

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("target", help="the target python file to generate unit tests for")
    args = parser.parse_args()

    script_path = args.target
    code = open(script_path, "r").read()
    tree = ast.parse(code)
    functions_info = extract_function_info(tree)  # getting how many functions and their names 


    input_list = collect_inputs(tree) # getting all the inputs in the code

    final_test_file_content = ""
    
    for i in range(len(functions_info)):
        
        function_name, num_arguments = functions_info[i]
        
        print(f"Function name: {function_name}, number of arguments: {num_arguments}")
        test_file_content =  hill_climbing(script_path, function_name, num_arguments, input_list, max_iterations=100)
        
        if i > 0:
            test_file_content = test_file_content.split("\n")[2:]
            test_file_content = "\n".join(test_file_content)

        final_test_file_content += "\n" + test_file_content
    

    test_file_name = os.path.join(os.path.dirname(script_path), "test_" + os.path.basename(script_path))

    with open(test_file_name, 'w') as f:
        f.write(final_test_file_content)