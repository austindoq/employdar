import asyncio, os, re, logging, pymongo
from mcp.server import MCPServer
from dotenv import load_dotenv
from datetime import datetime, timedelta, UTC
from zoneinfo import ZoneInfo
from bson import ObjectId

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
  """Format each job document for MCP Host readability."""
  return f"""
  Job Title: {job["job_title"]}
  Company: {job["company"]}
  Description: {job["description"]}
  Location: {job["location"]}
  URL: {job["url"]}
  Status: {job["status"]}
  Added On: {job["created_at"].astimezone(ZoneInfo("America/Vancouver"))}
  Job ID: {str(job["_id"])}
"""

# GET ALL JOBS WITHIN THE JOBS COLLECTION
@mcp.tool()
async def get_all_jobs() -> str:
  """Return all jobs applied to as a list."""

  try:
    cursor = db.jobs.find()
    result = await cursor.to_list(length=200)
  except Exception as error:
    logging.error(f"There was an error pulling job data: {error}")
    return f"There was an error getting all jobs: {error}"

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
    await db.jobs.insert_one({"job_title": job_title, "company": company, "description": description, "location": location, "url": url, "status": "applied", "created_at": datetime.now(UTC)})
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
      {"location": {"$regex": keyword, "$options": "i"}},
      {"status": {"$regex": keyword, "$options": "i"}}
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

#UPDATE AN APPLIED JOB'S APPLICATION STATUS 
@mcp.tool()
async def update_application_status(job_id: str, new_status: str) -> str:
  """
  Update the application status of a job in the database.

  Args:
    job_id: A job's ID that matches that specific job's MongoDB document _id.
    new_status: The new application status to update the 'status' field in the specific job posting's document.
  """
  #Must turn string of job_id into MongoDB ObjectID to return a match
  try:
    await db.jobs.update_one({"_id": ObjectId(job_id)}, {"$set": {"status": new_status.lower()}})
    return f"Application status updated to {new_status.lower()} successfully."
  except Exception as error:
    logging.info(f"There was an error updating the status of this application: {error}")
    return f"There was an error updating the status of this application: {error}"

#RETURN AGGREGATE JOB APPLICATION STATUS WITHIN TIMEFRAME
@mcp.tool()
async def return_application_statuses_by_timeframe(timeframe: str) -> str:
  """
  Return an aggregate count of jobs applied to grouped by application status based on timeframe.

  Arg: 
    timeframe: MUST be one of these keywords - "week", "month", or "year"
  """

  #Create cutoff to filter by
  if timeframe == "week":
    cutoff = datetime.now(UTC) - timedelta(days=7)
  elif timeframe == "month":
    cutoff = datetime.now(UTC) - timedelta(days=30)
  elif timeframe == "year":
    cutoff = datetime.now(UTC) - timedelta(days=365)
  else:
    return "Timeframe must be 'week', 'month', or 'year'."

  #Define the filter pipeline
  pipeline = [
    {"$match": {"created_at": {"$gte": cutoff}}},
    {"$group": {"_id": "$status", "count": {"$sum": 1}}}
  ]
  try:
    cursor = await db.jobs.aggregate(pipeline)
    result = await cursor.to_list(length=None)
  except Exception as error:
    logging.info(f"There was an error getting aggregate data: {error}")
    return f"There was an error getting aggregate data: {error}"

  buckets = []

  #Format data for return readability
  if not result:
    return "No groups within this timeframe."
  else: 
    for bucket in result:
      group = f"""\nStatus: {bucket["_id"]}\nCount: {bucket["count"]}
              """
      buckets.append(group)
    return "---".join(buckets)


if __name__ == "__main__":
  mcp.run(transport="stdio")