Create a Claude Code prompt that could customize a resume with a single interaction with Claude Code. Think about clever ways to tell it to use subagents to do work in parallel, and to use subagents to do the evaluator-optimization workflow. These are all of the MCP servers that I have configured:

• brave-search: connected
• context7: connected
• fetch: connected
• filesystem: connected
• git: connected
• github: connected
• graph-memory: connected
• magic: connected
• memory: connected
• puppeteer: connected
• sequential-thinking: connected
• taskmaster-ai: connected

If you are not familiar with these MCP servers, feel free to use your MCP tools to search for more information so that you can effectively tell Claude Code to use any of them to solve the problem. This prompt should be templatized for the following:

- Path to the resume
- URL to the job description

The prompt should include instructions to search the internet for more information about the applicant.