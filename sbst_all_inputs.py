import coverage
import subprocess
import argparse
import subprocess
import re
import random
import os
import ast 
import json
import csv
import string
import signal
from library import *

def collect_literals(node):
    literals = []
    if isinstance(node, (ast.Constant, ast.List, ast.Tuple)):
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            if node.value not in (True, False):
                literals.append(node.value)
        else:
            literals.append(node)
    for child in ast.iter_child_nodes(node):
        literals.extend(collect_literals(child))
    literals = list(set(literals))  # Remove duplicates
    print("literals = ", literals, "\n")
    return literals

def parse_literal(node):
    print("spec = ", ast.__spec__)
    if isinstance(node, ast.Constant): # ast.Num and ast.String are deprecated 
        print("node = ", node)
        print("kind = ", node.kind)
        print("node.n = ", node.n)
        print("node.s = ", node.s)
        if node.kind == str : # TODO: check doc for right test
            return node.s 
        else: 
            return node.n
    elif isinstance(node, ast.List):
        print("list")
        return [parse_literal(elem) for elem in node.elts]
    elif isinstance(node, ast.Tuple):
        print("tuple")
        return tuple(parse_literal(elem) for elem in node.elts)
    return None


def collect_inputs(node):
    literals = collect_literals(node)
    inputs = [parse_literal(literal) for literal in literals]
    inputs = [value for value in inputs if value is not None]
    print("inputs = ", inputs, "\n")
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

def fitness_function(script_path, function_name, arguments):
    
    result = [str(t) for t in arguments]
    # print("RESULT = ", result, "\n")

    target_module = os.path.basename(script_path).removesuffix(".py")
    second_part = ""
    for arg in arguments:
        second_part += f"\t{target_module}.{function_name}{arg}\n"
    #print(f"target module: {target_module}")
    # print("SECOND PART = ", second_part, "\n")


    test_file_content = f'''
import {target_module}
def test_sample():
{second_part}
    '''.strip()

    #print(f"Test file content: {test_file_content}")
    test_file_name = os.path.join(os.path.dirname(script_path), "test_" + os.path.basename(script_path))
    #print(f"Test file name: {test_file_name}")
    with open(test_file_name, 'w') as f:
        f.write(test_file_content)
    
    
    # Run the script with coverage
    run_command = ["coverage", "run", "-m", "pytest", test_file_name]
    # print("RUN COMMAND = ", run_command, "\n")
    try:
        subprocess.run(run_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=3.0)
    except subprocess.TimeoutExpired as e:
        print(f'coverage pytest timeout')
        return 0, test_file_content

    # Generate the coverage report
    report_command = ["coverage", "report"]
    report_output = subprocess.run(report_command, text=True, capture_output=True)
    #print(report_output.stdout)

    # Parse the coverage percentage from the report output
    coverage_line = report_output.stdout.splitlines()[2]
    coverage_percent_match = re.search(r'\d+%', coverage_line)
    if coverage_percent_match:
        coverage_percent = int(coverage_percent_match.group()[:-1])
        #print(f"Coverage: {coverage_percent}%")
        print("COVERAGE PERCENT = ", coverage_percent, "\n")

        return coverage_percent, test_file_content
    else:
        raise ValueError("Failed to parse coverage percentage")

def generate_random_element(argument_type):
    # Generate a random element of the chosen type
    if argument_type == "int":
        print("--int--")
        return random.randint(-100, 100)
    elif argument_type == "float":
        print("--float--")
        return random.uniform(-100.0, 100.0)
    elif argument_type == "str":
        print("--string--")
        return ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=5))
    elif argument_type.startswith("List"):
        print("--list--")
        return list(generate_random_element(argument_type[5:-1]) for _ in range(random.randint(1, 5)))
    elif argument_type == "tuple":
        print("--tuple--")
        return tuple(generate_random_element() for _ in range(random.randint(1, 5)))
    elif argument_type == "type(None)":
        print("--type none--")
        return None

def generate_random_tuple(arguments_types):
    # Generate a tuple with random elements
    return tuple(generate_random_element(arg_type) for arg_type in arguments_types)

def parse_type(text):
    # Get the type guess
    try:
      match = re.search(r'(\{.*?\})', text)
      answer_text = match.group(1)
      final = json.loads(answer_text)['types']
      return final
    except Exception as e:
        return None

# Modify hill_climbing to work with different types of arguments
def hill_climbing(script_path, function_name, num_arguments, inputs_list, args, max_iterations=100):
    with open(script_path, "r") as f:
        code = f.read()
    
    system_prompt_2 = f"""You are given a piece of code. Your job is to guess the
    type of each parameter of function. Return your guess as a list of python type. The size of the list 
    is equal to the number of arguments of the function. Also, each parameter type guess should not be an Union[] type.
    If there is an Union[] type, you should select the most probable type among the candidates.

    Return the test case within this json format: {{"types": ["type1", "type2", ...]}}
    The code is given below within triple ticks.
    """
    type_tuple = get_gpt_response(code, system_prompt_2, model="gpt-3.5-turbo-1106")
    print(f"type_tuple before parsing : {type_tuple}")
    type_tuple = parse_type(type_tuple)
    print(f"type_tuple after parsing : {type_tuple}")
    type_guess = []
    for ty in type_tuple:
        if ty.startswith("Union"):
            ty = ty[6:-1].split(',')[0]
        type_guess.append(ty)
    print(f'type_tuple again: {type_guess}')
    type_tuple = tuple(type_guess)

    arg_list = []
    # variable_type_str = type(inputs_list[0]).__name__ if inputs_list else None
    variable_type_str = type_tuple[0]
    print("variable_type = ", variable_type_str, "\n")

    # if len(inputs_list) == 0:
    #     random_tuple = generate_random_tuple(num_arguments, variable_type_str)
    # else:
    #     random_tuple = tuple(random.choice(inputs_list) for _ in range(num_arguments))
    #     print("random_tuple = ", random_tuple, "\n")
    random_tuple = generate_random_tuple(type_tuple)
    print("random_tuple = ", random_tuple, "\n")
        
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

    if args.gpt_feedback == "True":
        print(f"Using GPT Feedback")

    if args.gpt_init == "True":
        print(f"Using GPT Initialization") 
        #print("CODE = ", code, "\n")
        
        random_tuple = None 
        while random_tuple is None:
            random_tuple = get_gpt_response(code, system_prompt_0, model="gpt-3.5-turbo-1106")
            print(f"random_tuple before parsing : {random_tuple}")
            random_tuple = parse_answer(random_tuple)
            if random_tuple is None:
                continue
            random_tuple = tuple(random_tuple)
    ############################ 
        print("RANDOM TUPLE = ", random_tuple, "\n")
    arg_list.append(random_tuple)
    print(f"Initial arguments: {arg_list}")

    current_fitness, _ = fitness_function(script_path, function_name, arg_list)
    print(f"Current fitness: {current_fitness}")

    it = 0
    up = 0
    while (it < max_iterations) and (current_fitness < 100):
        #print(f"Iteration: {it}")
        # Generate a neighbor
        arg_list_2 = arg_list.copy()
        neighbor_index = random.randint(0, num_arguments - 1)
        variable_type_str = type_tuple[neighbor_index]
        tmp = list(arg_list_2[-1])
        #print("TMP INI  = list(arg_list_2[-1] = ", tmp, "\n")
        #tmp[neighbor_index] = random.choice(inputs_list)
        #tmp[neighbor_index] += random.randint(-5, 5)  # hyperparameter
        tmp = tuple(tmp)
        
        if variable_type_str == "int":
            print("int")
            tmp = tuple(
                value + random.randint(-5, 5) if i == neighbor_index else value
                for i, value in enumerate(tmp)
            )
        elif variable_type_str == "str":
            print("str")
            tmp = tuple(
                value + ''.join(random.choice(string.ascii_letters) for _ in range(3))
                if i == neighbor_index and random.choice([True, False])  # Add or remove letters randomly
                else value
                for i, value in enumerate(tmp)
            )
        elif variable_type_str.startswith("List") or variable_type_str.startswith("list"): # list
            print("list")
            nest_variable_type_str = variable_type_str[5:-1]
            # Handle list type
            if nest_variable_type_str == "int":
                print("int")
                tmp = list(tmp)
                if len(tmp[neighbor_index]) > 0:
                    nest_index = random.randint(0 , len(tmp[neighbor_index]) - 1)
                    tmp[neighbor_index][nest_index] = tmp[neighbor_index][nest_index] + random.randint(-5, 5)
                else:
                    tmp[neighbor_index].append(random.randint(-5, 5))
                tmp = tuple(tmp)
            elif nest_variable_type_str == "str":
                print("str")
                tmp = list(tmp)
                if len(tmp[neighbor_index]) > 0:
                    nest_index = random.randint(0 , len(tmp[neighbor_index]) - 1)
                    tmp[neighbor_index] = list(
                        value + ''.join(random.choice(string.ascii_letters) for _ in range(3))
                        if i == nest_index and random.choice([True, False])
                        else value
                        for i, value in enumerate(tmp)
                    )
                else:
                    tmp[neighbor_index].append(random.choice(string.ascii_letters))
                tmp = tuple(tmp)
            elif nest_variable_type_str.startswith("List") or nest_variable_type_str.startswith("list"): # list of list of int
                print("list")
                # Handle list type
                tmp = list(tmp)
                if len(tmp[neighbor_index]) > 0:
                    nest_index = random.randint(0 , len(tmp[neighbor_index]) - 1)
                    nest_nest_index = random.randint(0 , len(tmp[neighbor_index][nest_index]) - 1)
                    if len(tmp[neighbor_index][nest_index]) > 0:
                        tmp[neighbor_index][nest_index][nest_nest_index] = tmp[neighbor_index][nest_index][nest_nest_index] + random.randint(-5, 5)
                    else:
                        tmp[neighbor_index][nest_index].append(random.randint(-5, 5))
                else:
                    tmp[neighbor_index].append(list(random.randint(-5, 5) for _ in range(random.randint(0, 5))))
                tmp = tuple(tmp)
            else:
                # Handle other types as needed
                pass
        else:
            # Handle other types as needed
            pass
        
        
        #print("TMP = tuple(tmp) = ", tmp, "\n\n")
        

        if it - up > 3:  # if stuck in a local optimum, make a jump
            # traditional jump
            if args.gpt_feedback != "True":
                tmp = generate_random_tuple(type_tuple) ###TODO: adapt to all input types 
                print("LEN 0 -- TMP = ", tmp, "\n\n")
                # if len(inputs_list) == 0:
                #     tmp = generate_random_tuple(type_tuple) ###TODO: adapt to all input types 
                #     print("LEN 0 -- TMP = ", tmp, "\n\n")
                #     #tmp = tuple(random.randint(-100, 100) for _ in range(num_arguments))
                # else:
                #     if variable_type_str == "int":
                #         rand = random.random() # 3 cases: 1. random int in proper range, 2. random choice from int_list, 3. random int from -100 to 100
                #         if rand < 0.4:
                #             tmp = tuple(random.randint(min(inputs_list), max(inputs_list)) for _ in range(num_arguments))
                #         elif 0.4 <= rand < 0.8:
                #             tmp = tuple(random.choice(inputs_list) for _ in range(num_arguments))
                #         else:
                #             tmp = tuple(random.randint(-100, 100) for _ in range(num_arguments))
                #     elif variable_type_str == "str":
                #         rand = random.random()
                #         if rand < 0.4:
                #             tmp = tuple(value + ''.join(random.choice(string.ascii_letters) for _ in range(3)) for value in tmp)
                #             print("debut\n")
                #         elif 0.4 <= rand < 0.8:
                #             tmp = tuple(value + random.choice(inputs_list) for value in tmp)
                #             print("milieu\n")
                #         else:
                #             tmp = tuple(value + ''.join(random.choice(string.ascii_letters) for _ in range(3)) for value in tmp)
                #             print("fin\n")

            
            # gpt jump
            if args.gpt_feedback == "True":
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
    print(f"file name: {args.target}")
    print(f"Final arguments: {arg_list}")
    print(f"There are {len(arg_list)} test cases")
    print(f"Final fitness: {final_fitness}")
    print(f"Finished at iteration: {it}")
    print(f"gpt init: {args.gpt_init}")
    print(f"gpt feedback: {args.gpt_feedback}")

    filename = 'results_all_inputs.csv'

    # Check if the file already exists to decide whether to write headers
    file_exists = os.path.isfile(filename)

    # Open the file in append mode
    with open(filename, 'a', newline='') as csvfile:
        # Create a CSV writer object
        csvwriter = csv.writer(csvfile)

        # Write the header if the file is new
        if not file_exists:
            csvwriter.writerow(['File Name', 'Final Arguments', 'Number of Test Cases', 'Final Fitness', 'Finished at Iteration', 'GPT Init', 'GPT Feedback'])

        # Write the data
        csvwriter.writerow([args.target, str(arg_list), len(arg_list), final_fitness, it, args.gpt_init, args.gpt_feedback])
    return final_test_file_content

if __name__ == "__main__":
    
    current_directory = os.getcwd()
    #print("Current Working Directory:", current_directory)

    parser = argparse.ArgumentParser()
    parser.add_argument("target", help="the target python file to generate unit tests for")
    parser.add_argument("gpt_init", help="whether to use gpt initialization or not. True of False")
    parser.add_argument("gpt_feedback", help="whether to use gpt feedback or not. True of False")
    args = parser.parse_args()

    script_path = args.target
    code = open(script_path, "r").read()
    tree = ast.parse(code)
    functions_info = extract_function_info(tree)  # getting how many functions and their names 


    input_list = collect_inputs(tree) # getting all the inputs in the code
    print("input_list = ", input_list, "\n")
    final_test_file_content = ""
    
    for i in range(len(functions_info)):
        print(i)
        
        function_name, num_arguments = functions_info[i]
        
        print(f"Function name: {function_name}, number of arguments: {num_arguments}")
        test_file_content =  hill_climbing(script_path, function_name, num_arguments, input_list, args, max_iterations=100)
        
        if i > 0:
            test_file_content = test_file_content.split("\n")[2:]
            test_file_content = "\n".join(test_file_content)

        final_test_file_content += "\n" + test_file_content
    

    test_file_name = os.path.join(os.path.dirname(script_path), "test_" + os.path.basename(script_path))

    with open(test_file_name, 'w') as f:
        f.write(final_test_file_content)