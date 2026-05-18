"""CrewAI scraper crew: researcher -> analyst agents, all through tierproxy.

Demonstrates how the proxy + smart routing benefits multi-agent setups where
many concurrent web fetches happen — cost-aware routing actively shaves cents
per task.

Install: pip install crewai 'crewai-tools[scrape]' tierproxy
"""

import os

from crewai import Agent, Crew, Process, Task
from crewai_tools import ScrapeWebsiteTool
from tierproxy import ProxyURL, TierProxy

client = TierProxy(routing="cheapest")  # auto-pick cheapest upstream every fetch
proxy = ProxyURL(
    api_key=os.environ["TIERPROXY_API_KEY"],
    country="US",
    session_id="crewai-crew-1",
)

# crewai_tools.ScrapeWebsiteTool wraps requests under the hood
scrape_tool = ScrapeWebsiteTool(
    website_url=None,  # set per-task
    headers=proxy.headers(),
    proxies={"http": proxy.http_url(), "https": proxy.http_url()},
)

researcher = Agent(
    role="Web Researcher",
    goal="Find the top 5 most-discussed posts about LLM agents in the last 24h.",
    tools=[scrape_tool],
    backstory="You browse HN, Reddit, and Twitter. You only return URLs.",
)
analyst = Agent(
    role="Content Analyst",
    goal="Read the URLs and produce a 1-paragraph thesis on what's trending.",
    tools=[scrape_tool],
    backstory="You're a sharp technical writer who reads carefully and is skeptical of hype.",
)

research_task = Task(
    description="List 5 trending agent-related posts as URLs.",
    expected_output="bullet list of 5 URLs",
    agent=researcher,
)
analyze_task = Task(
    description="Read each URL and write the thesis paragraph.",
    expected_output="single paragraph, max 200 words",
    agent=analyst,
)

crew = Crew(
    agents=[researcher, analyst],
    tasks=[research_task, analyze_task],
    process=Process.sequential,
)
print(crew.kickoff())

# Cost report
usage = client.usage.get()
print(f"\nTotal cost this crew run + month: ${usage.total_cost_usd:.4f}")
