import os
import subprocess
import re
from groq import Groq

# Initialize Groq client with API key
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Function to execute the COBOL batch payment processing program
def execute_cobol_program():
    # Read the contents of the OUTPUT.DAT file
    with open('OUTPUT.DAT', 'r') as file:
        output_data = file.read()
    print(f"COBOL program output from file:\n{output_data}")  # New print statement to log output from file
    return output_data

# Function to process transaction data using Groq API
def process_transactions_with_groq(transactions):
    # Iterate over transactions
    for transaction in transactions:
        # Construct the prompt based on the transaction type
        if transaction['transaction_code'] == 'EP':
            operation = "add"
        elif transaction['transaction_code'] == 'DL':
            operation = "subtract"
        else:
            print(f"Unknown transaction code: {transaction['transaction_code']}")
            continue

        prompt = f"Please {operation} {transaction['amount']} to the total balance."

        # Choose an appropriate model ID based on the task
        model_id = "llama3-70b-8192"  # Updated model ID

        # Create a payload for the API call
        payload = {
            "messages": [{"role": "system", "content": prompt}],
            "model": model_id,
            "temperature": 0,  # We want deterministic results for arithmetic operations
            "max_tokens": 50,  # A small number of tokens should be sufficient for arithmetic operations
        }

        # Make an API call to process the prompt
        response = client.chat.completions.create(**payload)

        # Extract the response content
        processed_content = response.choices[0].message.content

        # Use the processed content to update the transaction processing logic
        update_transaction_logic(transaction, processed_content)

# Function to extract text from a transaction record
def extract_text_from_transaction(transaction):
    # Extract the description field from the transaction record
    return transaction.get("description", "")

# Function to update transaction processing logic with insights from Groq API
def update_transaction_logic(transaction, processed_content):
    print(f"Entering update_transaction_logic for transaction {transaction['id']} with content: {processed_content}")
    # Updated regex patterns to be more flexible in capturing balance information
    direct_balance_pattern = re.compile(r"balance is (\d+(\.\d{1,2})?)", re.IGNORECASE)
    operation_balance_pattern = re.compile(r"total balance,? and I'll be happy to (add|subtract) (\d+(\.\d{1,2})?)", re.IGNORECASE)

    direct_balance_match = direct_balance_pattern.search(processed_content)
    operation_balance_match = operation_balance_pattern.search(processed_content)
    print(f"Regex search completed for transaction {transaction['id']}")
    print(f"Direct balance match: {direct_balance_match}")
    print(f"Operation balance match: {operation_balance_match}")

    if direct_balance_match:
        new_balance = float(direct_balance_match.group(1))
        transaction['balance'] = new_balance
        print(f"Transaction {transaction['id']} updated with new balance: {new_balance}")
    elif operation_balance_match:
        operation = operation_balance_match.group(1).lower()
        operation_amount = float(operation_balance_match.group(2))
        if 'balance' not in transaction:
            transaction['balance'] = 0.0
        current_balance = transaction['balance']
        if operation == "subtract":
            new_balance = current_balance - operation_amount
        elif operation == "add":
            new_balance = current_balance + operation_amount
        transaction['balance'] = new_balance
        print(f"Transaction {transaction['id']} updated with new balance: {new_balance}")
    else:
        print(f"Could not extract new balance from Groq response for transaction {transaction['id']}: {processed_content}")

    print(f"Exiting update_transaction_logic for transaction {transaction['id']}")

# Function to parse the COBOL program output into a list of transactions
def parse_cobol_output(output):
    # Split the output into lines
    lines = output.strip().split('\n')
    transactions = []
    # Regex pattern to match the transaction lines more flexibly
    transaction_line_pattern = re.compile(r'^\d{6}\s+\d+\.\d{2}[EPDL]{2}.*$')
    # Regex pattern to extract the amount
    amount_pattern = re.compile(r'\d+\.\d{2}')
    for line in lines:
        print(f"Processing line: {line}")  # Print each line before processing
        # Skip lines that do not match the transaction line format
        if not transaction_line_pattern.match(line):
            print(f"Line does not match pattern: {line}")  # Print mismatch message
            continue
        print(f"Line matches pattern: {line}")  # Print match message

        # Parse the line according to the COBOL output format
        account_number = line[0:6]
        # Extract the amount using regex
        amount_match = amount_pattern.search(line)
        if amount_match:
            amount = amount_match.group()
        else:
            print(f"Error extracting amount for line: {line}")
            continue  # Skip this transaction if amount cannot be extracted

        # Corrected indices to capture the transaction code
        transaction_code = line[15:17]
        description = line[19:].strip()  # Strip to remove any leading/trailing whitespace

        # Validate and convert amount to float
        try:
            amount_float = float(amount)
        except ValueError:
            # Log an error message if the amount cannot be converted
            print(f"Error converting amount to float for line: {line}")
            continue  # Skip this transaction

        # Create a transaction dictionary
        transaction = {
            "id": account_number,
            "transaction_code": transaction_code,
            "amount": amount_float,
            "description": description
        }
        transactions.append(transaction)
        print(f"Added transaction: {transaction}")  # Debugging print statement

    print(f"Total transactions parsed: {len(transactions)}")  # Debugging print statement
    return transactions  # Ensure a list is always returned, even if it's empty

# Function to summarize transactions using Groq's output
def summarize_transactions(transactions):
    # Summarize the transactions by transaction code
    transaction_summary = {}
    for transaction in transactions:
        code = transaction.get("transaction_code")
        amount = transaction.get("amount", 0)
        if code in transaction_summary:
            transaction_summary[code] += amount
        else:
            transaction_summary[code] = amount
    # Print the transaction summary
    print("Transaction Summary:")
    for code, amount in transaction_summary.items():
        print(f"Transaction Code: {code}, Total Amount: {amount}")

# Main function to orchestrate the batch payment processing and Groq integration
def main():
    # Execute the COBOL program and get its output
    cobol_output = execute_cobol_program()

    # Parse the COBOL program output into a list of transactions
    transactions = parse_cobol_output(cobol_output)

    # Process transactions with Groq API
    process_transactions_with_groq(transactions)

    # Summarize transactions using Groq's output
    summarize_transactions(transactions)

if __name__ == "__main__":
    main()
