import asyncio
import logging
from mcp.server import MCPServer
from dotenv import load_dotenv
import os
import pymongo

#LOGGING CONFIG
logging.basicConfig(level=logging.INFO)

#ENVIRONMENT VARIABLES
load_dotenv()
MONGO_CONNECTION = os.getenv("MONGO_CONNECTION")

#DATABASE CONFIG
client = pymongo.AsyncMongoClient(MONGO_CONNECTION)
db = client.employdar

#MCP SERVER INSTANCE 
mcp = MCPServer("Employdar")

# GET ALL JOBS WITHIN THE JOBS COLLECTION
@mcp.tool()
async def get_all_jobs() -> str:
  """Return all jobs applied to as a list."""
  cursor = db.jobs.find()
  result = await cursor.to_list(length=20)
  return "\n---\n".join(result)

# ADD A JOB TO THE DATABASE 
@mcp.tool()
async def add_job(job_title: str, company: str, description: str, location: str) -> str:
  """
  Add a single job to the database.

  Args:
    job_title: The job title.
    company: The company name.
    description: Derived from the job posting description, this should be a concise (<100 words) description of the requirements and responsibilities associated with the job.
    location: The district within the lower mainland BC, Canada of the workplace or working arrangement. 
  """
  try:
    await db.jobs.insert_one({"job_title": job_title, "company": company, "description": description, "location": location})
    return f"Successfully saved {job_title} at {company}"
  except Exception as error:
    logging.error(f"There was an error saving the job to the job database: {Exception}")
    return f"There was an error saving this job to the job database: {Exception}"



if __name__ == "__main__":
  mcp.run(transport="stdio")