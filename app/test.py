from services.triage_service import triage_message

result = triage_message("Where is my order?")
print(type(result))
print(result)