#!/bin/bash

# Set file paths
PROMPT_PATH="/Users/joshuaoliphant/Library/CloudStorage/Dropbox/python_workspace/ResumeAIAssistant/claude_code_resume_prompt.md"
RESUME_PATH="/Users/joshuaoliphant/Library/CloudStorage/Dropbox/python_workspace/ResumeAIAssistant/original_resume.md"
JOB_PATH="/Users/joshuaoliphant/Library/CloudStorage/Dropbox/python_workspace/ResumeAIAssistant/job_description.txt"
OUTPUT_PATH="/Users/joshuaoliphant/Library/CloudStorage/Dropbox/python_workspace/ResumeAIAssistant/customized_resume_output.md"

# Process the prompt file, replacing placeholders
PROCESSED_PROMPT=$(cat "$PROMPT_PATH" | sed "s#{{RESUME_PATH}}#$RESUME_PATH#g; s#{{JOB_PATH}}#$JOB_PATH#g")

# Save processed prompt to a temporary file
TEMP_PROMPT_FILE=$(mktemp)
echo "$PROCESSED_PROMPT" > "$TEMP_PROMPT_FILE"

echo "Starting Claude Code to customize resume..."
echo "This may take several minutes to complete."

# Run Claude Code with the processed prompt and stream output to console while saving to file
# Note: You might need to adjust this command based on your Claude CLI setup
claude code -p "$(cat $TEMP_PROMPT_FILE)" --output-format text | tee "$OUTPUT_PATH"

# Check if the command was successful
if [ $? -eq 0 ]; then
    echo "Resume customization completed successfully!"
    echo "Customized resume saved to: $OUTPUT_PATH"
else
    echo "An error occurred during resume customization."
    echo "Please check if your Claude API key is properly set up."
fi

# Clean up temporary file
rm "$TEMP_PROMPT_FILE"