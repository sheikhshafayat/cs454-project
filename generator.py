import openai
import os
import json
import sys
with open("openai-api-.txt", "r") as f: # put your own api
    line = f.readline()    

os.environ["OPENAI_API_KEY"] = line
openai.api_key = os.getenv("OPENAI_API_KEY")
from library import *
from datasets import load_dataset

if len(sys.argv) != 2:
    print("There must be 2 arguments : 'generator.py' and an integer a that 0 <= a < 5000.")
    sys.exit()
    
number = int(sys.argv[1])
if number < 0 or number >= 5000:
    print("The integer must be nonnegative, and lower than 5000.")
    sys.exit()

dataset = load_dataset("codeparrot/apps")

one_data = dataset["train"][number]
one_data_question = one_data["question"]
#print(one_data, "\n\n")
#print(one_data["question"])
one_data = json.loads(one_data["solutions"])
#print("\n -- Solution -- \n")
#print(one_data[0])

with open(f"examples/function_{number}.py", "w", encoding="UTF-8") as f:
    #f.write('"""\n')
    #f.write(one_data_question)
    #f.write('\n"""\n\n')
    f.write(one_data[0])
    f.close()
