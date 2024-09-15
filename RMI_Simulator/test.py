from datetime import datetime

now = datetime.now()
formatted = now.strftime('%B %d, %Y %H:%M:%S')
print(f"Formatted date: {formatted}")
