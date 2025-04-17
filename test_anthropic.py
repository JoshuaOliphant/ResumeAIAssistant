import inspect
from anthropic import Anthropic
import anthropic

print(f"Anthropic SDK Version: {anthropic.__version__}")

# Initialize the client
client = Anthropic()

# Print out the available parameters for the create method
print("\nAnthropic.messages.create parameters:")
create_method = client.messages.create
signature = inspect.signature(create_method)
print(signature)
print("\nParameter details:")
for param_name, param in signature.parameters.items():
    print(f"  {param_name}: {param.annotation}")