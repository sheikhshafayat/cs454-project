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
import csv


def collect_ints(node):
    ints = []
    if isinstance(node, ast.Num):  
        ints.append(node.n)
    elif isinstance(node, ast.Constant) and isinstance(node.value, int):  
        # Check if the value is not True or False before appending
        if node.value not in (True, False):
            ints.append(node.value)
    for child in ast.iter_child_nodes(node):
        ints.extend(collect_ints(child))
    ints = list(set(ints))  # Remove duplicates
    return ints

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
    target_module = os.path.basename(script_path).removesuffix(".py")
    second_part = ""
    for arg in arguments:
        second_part += f"\t{target_module}.{function_name}{arg}\n"
    #print(f"target module: {target_module}")

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
    subprocess.run(run_command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Generate the coverage report
    report_command = ["coverage", "report"]
    report_output = subprocess.run(report_command, text=True, capture_output=True)
    #print(report_output.stdout)

    # Parse the coverage percentage from the report output
    coverage_line = report_output.stdout.splitlines()[-1]
    coverage_percent_match = re.search(r'(\d+%)', coverage_line)
    if coverage_percent_match:
        coverage_percent = int(coverage_percent_match.group(1)[:-1])
        #print(f"Coverage: {coverage_percent}%")
        return coverage_percent, test_file_content
    else:
        raise ValueError("Failed to parse coverage percentage")


def hill_climbing(script_path, function_name, num_arguments, int_list, args, max_iterations=1000):
    
    arg_list = []
    # random initialization


    if len(int_list) == 0:
        random_tuple = tuple(random.randint(-100, 100) for _ in range(num_arguments))
    else:
        #random_tuple = tuple(random.choice(int_list) for _ in range(num_arguments))
        random_tuple = tuple(random.randint(min(int_list), max(int_list)) for _ in range(num_arguments))


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
        with open(script_path, "r") as f:
            code = f.read()
        
        random_tuple = None 
        while random_tuple is None:
            random_tuple = get_gpt_response(code, system_prompt_0, model="gpt-3.5-turbo-1106")
            # print(f"random_tuple: {random_tuple}")
            random_tuple = parse_answer(random_tuple)
            if random_tuple is None:
                continue
            random_tuple = tuple(random_tuple)
    ############################

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
        tmp[neighbor_index] += random.randint(-5, 5) # hyperparameter
        tmp = tuple(tmp)
        
        if it - up > 3: # if stuck in a local optimum, make a jump
            # traditional jump
            if args.gpt_feedback != "True":
                if len(int_list) == 0:
                    tmp = tuple(random.randint(-100, 100) for _ in range(num_arguments))
                else:
                    rand = random.random() # three cases: 1. random int in proper range, 2. random choice from int_list, 3. random int from -100 to 100
                    if rand < 0.4:
                        tmp = tuple(random.randint(min(int_list), max(int_list)) for _ in range(num_arguments))
                    elif (rand < 0.8) and (rand >= 0.4):    
                        tmp = tuple(random.choice(int_list) for _ in range(num_arguments))
                    else:
                        tmp = tuple(random.randint(-100, 100) for _ in range(num_arguments))
            
            # gpt jump
            if args.gpt_feedback == "True":
                prompt = f"Code:\n{code}\n\nCurrent Test Cases:\n{str(arg_list_2)}"
                # print(f"here")
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

    filename = 'results.csv'

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
    parser = argparse.ArgumentParser()
    parser.add_argument("target", help="the target python file to generate unit tests for")
    parser.add_argument("gpt_init", help="whether to use gpt initialization or not. True of False")
    parser.add_argument("gpt_feedback", help="whether to use gpt feedback or not. True of False")
    args = parser.parse_args()

    script_path = args.target
    code = open(script_path, "r").read()
    tree = ast.parse(code)
    functions_info = extract_function_info(tree) # getting how many functions and their names
    int_list = collect_ints(tree) # getting all the ints in the code

    final_test_file_content = ""
    
    for i in range(len(functions_info)):
        
        function_name, num_arguments = functions_info[i]
        
        print(f"Function name: {function_name}, number of arguments: {num_arguments}")
        test_file_content =  hill_climbing(script_path, function_name, num_arguments, int_list, args, max_iterations=100)
        
        if i > 0:
            test_file_content = test_file_content.split("\n")[2:]
            test_file_content = "\n".join(test_file_content)

        final_test_file_content += "\n" + test_file_content
    

    test_file_name = os.path.join(os.path.dirname(script_path), "test_" + os.path.basename(script_path))

    with open(test_file_name, 'w') as f:
        f.write(final_test_file_content)


