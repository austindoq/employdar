import asyncio, os, re, logging, pymongo
from mcp.server import MCPServer
from dotenv import load_dotenv
from datetime import datetime, UTC
from zoneinfo import ZoneInfo

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

#FORMAT HELPER FUNCTION
def format_job(job: dict) -> str:
  return f"""
  Job Title: {job["job_title"]}
  Company: {job["company"]}
  Description: {job["description"]}
  Location: {job["location"]}
  URL: {job["url"]}
  Added On: {job["created_at"].astimezone(ZoneInfo("America/Vancouver"))}
"""

# GET ALL JOBS WITHIN THE JOBS COLLECTION
@mcp.tool()
async def get_all_jobs() -> str:
  """Return all jobs applied to as a list."""
  cursor = db.jobs.find()
  result = await cursor.to_list(length=200)

  if not result:
    return f"No jobs in database to return yet."
  else:
    jobs = [format_job(job) for job in result]
    return "\n---\n".join(jobs)

# ADD A JOB TO THE DATABASE 
@mcp.tool()
async def add_job(job_title: str, company: str, description: str, location: str, url: str) -> str:
  """
  Add a single job to the database.

  Args:
    job_title: The job title.
    company: The company name.
    description: Derived from the job posting description, this should be a concise (<100 words) description of the requirements and responsibilities associated with the job.
    location: The district within the lower mainland BC, Canada of the workplace or working arrangement. 
    url: The URL of the job posting.
  """
  try:
    await db.jobs.insert_one({"job_title": job_title, "company": company, "description": description, "location": location, "url": url, "created_at": datetime.now(UTC)})
    return f"Successfully saved {job_title} at {company}"
  except Exception as error:
    logging.error(f"There was an error saving the job to the job database: {error}")
    return f"There was an error saving this job to the job database: {error}"

#SEARCH JOBS COLLECTION BY A KEYWORD
@mcp.tool()
async def search_jobs_by_keyword(keyword: str) -> str:
  """
  Search the jobs collection by keyword.

  Args:
    keyword: A string to search the jobs collection with.
  """

  #Handle special regex characters in keyword
  keyword = re.escape(keyword)

  #Search for the keyword over these document fields
  search_query = {
    "$or" : [
      {"job_title": {"$regex": keyword, "$options": "i"}},
      {"company": {"$regex": keyword, "$options": "i"}},
      {"description": {"$regex": keyword, "$options": "i"}},
      {"location": {"$regex": keyword, "$options": "i"}}
    ]
  }

  try:
    cursor = db.jobs.find(search_query)
    result = await cursor.to_list(length=200)

    if not result:
      return f"No jobs found for that keyword."
    else:
      jobs = [format_job(job) for job in result]
      return "\n---\n".join(jobs)
  except Exception as error:
    logging.error(f"There was an error finding job postings that match your search: {error}")
    return f"There was an error finding job postings that match your search: {error}"

if __name__ == "__main__":
  mcp.run(transport="stdio")