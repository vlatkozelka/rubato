from services.policy_qa_service import answer_policy_question

result = answer_policy_question("How many days do I have to return an opened software license?")
print(f"{result}\n\n\n\n")

# the actual stress test — the contradiction
result2 = answer_policy_question("My jacket arrived defective, how long do I have to report it?")
print(f"{result2}\n\n\n\n")

# the honest "I don't know" case — ask something not in any doc
result3 = answer_policy_question("Do you offer gift wrapping?")
print(f"{result3}\n\n\n\n")