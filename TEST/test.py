print("Hello world")

import os
from dotenv import load_dotenv
load_dotenv()

print(os.getenv("KIS_ACCESS_KEY"))
