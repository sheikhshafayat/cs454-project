# How to test
First, you have to install modules via requirements.txt.

    pip install requirements.txt

Second, you have to get an openai api key and save it in 'openai-api-.txt'.
And then, you can run test with command below.

    python sbst_all_inputs.py [TARGET EXAMPLE PATH] [GPT INIT] [GPT FEEDBACK]

If you want to test 'ex/example1.py' with GPT initialization and GPT feedback, you have to enter like this.

    python sbst_all_inputs.py ex/example1.py True True