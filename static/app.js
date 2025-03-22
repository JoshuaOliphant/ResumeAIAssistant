document.addEventListener('DOMContentLoaded', function() {
    // API base URL
    const API_BASE_URL = '/api/v1';
    
    // Get form elements
    const resumeForm = document.getElementById('resume-form');
    const jobForm = document.getElementById('job-form');
    const jobUrlForm = document.getElementById('job-url-form');
    const analyzeBtn = document.getElementById('analyze-btn');
    const customizeBtn = document.getElementById('customize-btn');
    const coverLetterBtn = document.getElementById('cover-letter-btn');
    const selectResume = document.getElementById('select-resume');
    const selectJob = document.getElementById('select-job');
    const resultsContainer = document.getElementById('results-container');
    
    // Initialize the app
    init();
    
    // Initialize by loading resumes and job descriptions
    function init() {
        loadResumes();
        loadJobDescriptions();
    }
    
    // Load all resumes
    function loadResumes() {
        fetch(`${API_BASE_URL}/resumes/`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch resumes');
            }
            return response.json();
        })
        .then(data => {
            // Clear options except first placeholder
            selectResume.innerHTML = '<option selected>Choose your resume...</option>';
            
            // Add resumes to select
            data.forEach(resume => {
                const option = document.createElement('option');
                option.value = resume.id;
                option.textContent = resume.title;
                selectResume.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Error loading resumes:', error);
            showAlert('danger', 'Failed to load resumes. Please try again later.');
        });
    }
    
    // Load all job descriptions
    function loadJobDescriptions() {
        fetch(`${API_BASE_URL}/jobs/`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch job descriptions');
            }
            return response.json();
        })
        .then(data => {
            // Clear options except first placeholder
            selectJob.innerHTML = '<option selected>Choose a job description...</option>';
            
            // Add job descriptions to select
            data.forEach(job => {
                const option = document.createElement('option');
                option.value = job.id;
                option.textContent = job.title + (job.company ? ` - ${job.company}` : '');
                selectJob.appendChild(option);
            });
        })
        .catch(error => {
            console.error('Error loading job descriptions:', error);
            showAlert('danger', 'Failed to load job descriptions. Please try again later.');
        });
    }
    
    // Handle file upload for resume
    const resumeFileInput = document.getElementById('resume-file');
    if (resumeFileInput) {
        resumeFileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(e) {
                    const content = e.target.result;
                    // Set the content to the textarea for preview (optional)
                    // This allows users to still edit the content after uploading
                    document.getElementById('resume-content').value = content;
                    // Switch to manual tab to show preview
                    document.getElementById('manual-tab').click();
                };
                reader.readAsText(file);
            }
        });
    }
    
    // Resume form submission
    if (resumeForm) {
        resumeForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Get form data
            const title = document.getElementById('resume-title').value;
            let content;
            
            // Check if file was uploaded
            const file = document.getElementById('resume-file').files[0];
            if (file) {
                // File is handled by the change event, get content from textarea where we stored it
                content = document.getElementById('resume-content').value;
            } else {
                content = document.getElementById('resume-content').value;
            }
            
            // Validate form data
            if (!title) {
                showAlert('warning', 'Please provide a title for your resume.');
                return;
            }
            
            if (!content) {
                showAlert('warning', 'Please enter resume content or upload a Markdown file.');
                return;
            }
            
            // Disable submit button
            const submitBtn = resumeForm.querySelector('button[type="submit"]');
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';
            
            // Send request to API
            fetch(`${API_BASE_URL}/resumes/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    title: title,
                    content: content
                })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to save resume');
                }
                return response.json();
            })
            .then(data => {
                // Show success message
                showAlert('success', 'Resume saved successfully!');
                
                // Reset form
                resumeForm.reset();
                
                // Reload resumes
                loadResumes();
                
                // Switch to analyze tab
                document.getElementById('analyze-tab').click();
            })
            .catch(error => {
                console.error('Error saving resume:', error);
                showAlert('danger', 'Failed to save resume. Please try again later.');
            })
            .finally(() => {
                // Re-enable submit button
                submitBtn.disabled = false;
                submitBtn.innerHTML = 'Save Resume';
            });
        });
    }
    
    // Job description form submission
    if (jobForm) {
        jobForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Get form data
            const title = document.getElementById('job-title').value;
            const company = document.getElementById('company').value;
            const description = document.getElementById('job-description').value;
            
            // Validate form data
            if (!title || !description) {
                showAlert('warning', 'Please fill in all required fields.');
                return;
            }
            
            // Disable submit button
            const submitBtn = jobForm.querySelector('button[type="submit"]');
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Saving...';
            
            // Send request to API
            fetch(`${API_BASE_URL}/jobs/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    title: title,
                    company: company,
                    description: description
                })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to save job description');
                }
                return response.json();
            })
            .then(data => {
                // Show success message
                showAlert('success', 'Job description saved successfully!');
                
                // Reset form
                jobForm.reset();
                
                // Reload job descriptions
                loadJobDescriptions();
                
                // Switch to analyze tab
                document.getElementById('analyze-tab').click();
            })
            .catch(error => {
                console.error('Error saving job description:', error);
                showAlert('danger', 'Failed to save job description. Please try again later.');
            })
            .finally(() => {
                // Re-enable submit button
                submitBtn.disabled = false;
                submitBtn.innerHTML = 'Save Job Description';
            });
        });
    }
    
    // Job URL form submission
    if (jobUrlForm) {
        jobUrlForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Get form data
            const url = document.getElementById('job-url').value;
            const submitBtn = document.getElementById('job-url-submit');
            const submitText = document.getElementById('job-url-submit-text');
            const spinner = document.getElementById('job-url-spinner');
            const alertEl = document.getElementById('job-url-alert');
            const successEl = document.getElementById('job-url-success');
            
            // Validate form data
            if (!url) {
                alertEl.textContent = 'Please enter a valid URL.';
                alertEl.classList.remove('d-none');
                return;
            }
            
            // Hide any previous alerts
            alertEl.classList.add('d-none');
            successEl.classList.add('d-none');
            
            // Show loading state
            submitBtn.disabled = true;
            submitText.textContent = 'Importing...';
            spinner.classList.remove('d-none');
            
            // Add timeout for better user experience with slow connections
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 30000); // 30-second timeout
            
            // Send request to API
            fetch(`${API_BASE_URL}/jobs/from-url/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    url: url
                }),
                signal: controller.signal
            })
            .then(response => {
                clearTimeout(timeoutId);
                
                if (!response.ok) {
                    return response.json().then(errData => {
                        throw new Error(errData.detail || 'Failed to import job description');
                    });
                }
                return response.json();
            })
            .then(data => {
                // Show success message
                successEl.classList.remove('d-none');
                
                // Fill form fields for preview/editing
                document.getElementById('job-title').value = data.title || '';
                document.getElementById('company').value = data.company || '';
                document.getElementById('job-description').value = data.description || '';
                
                showAlert('success', 'Job description imported successfully!');
                
                // Don't reset form or switch tabs - let user review the imported data first
            })
            .catch(error => {
                console.error('Error importing job description:', error);
                
                // Show error message
                if (error.name === 'AbortError') {
                    alertEl.textContent = 'The request took too long to complete. The website might be unavailable or too complex to process.';
                } else {
                    alertEl.textContent = 'Failed to import job description. Please try a different URL or enter the details manually.';
                }
                alertEl.classList.remove('d-none');
                
                showAlert('danger', 'Failed to import job description.');
            })
            .finally(() => {
                // Reset UI state
                submitBtn.disabled = false;
                submitText.textContent = 'Import Job Description';
                spinner.classList.add('d-none');
            });
        });
    }
    
    // Analyze ATS Compatibility
    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', function() {
            const resumeId = selectResume.value;
            const jobId = selectJob.value;
            
            // Validate selection
            if (resumeId === 'Choose your resume...' || jobId === 'Choose a job description...') {
                showAlert('warning', 'Please select both a resume and a job description.');
                return;
            }
            
            // Show loading state
            analyzeBtn.disabled = true;
            analyzeBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Analyzing...';
            resultsContainer.innerHTML = '<div class="d-flex justify-content-center"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div></div>';
            resultsContainer.classList.remove('d-none');
            
            // Send request to API
            fetch(`${API_BASE_URL}/ats/analyze/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    resume_id: resumeId,
                    job_description_id: jobId
                })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to analyze resume');
                }
                return response.json();
            })
            .then(data => {
                // Display results
                displayATSResults(data);
            })
            .catch(error => {
                console.error('Error analyzing resume:', error);
                showAlert('danger', 'Failed to analyze resume. Please try again later.');
                resultsContainer.classList.add('d-none');
            })
            .finally(() => {
                // Re-enable button
                analyzeBtn.disabled = false;
                analyzeBtn.innerHTML = 'Analyze ATS Compatibility';
            });
        });
    }
    
    // Customize Resume
    if (customizeBtn) {
        customizeBtn.addEventListener('click', function() {
            const resumeId = selectResume.value;
            const jobId = selectJob.value;
            
            // Validate selection
            if (resumeId === 'Choose your resume...' || jobId === 'Choose a job description...') {
                showAlert('warning', 'Please select both a resume and a job description.');
                return;
            }
            
            // Show loading state
            customizeBtn.disabled = true;
            customizeBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Customizing...';
            resultsContainer.innerHTML = '<div class="alert alert-info">Customizing your resume with Claude AI. This may take a minute...</div><div class="d-flex justify-content-center"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div></div>';
            resultsContainer.classList.remove('d-none');
            
            // Send request to API
            fetch(`${API_BASE_URL}/customize/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    resume_id: resumeId,
                    job_description_id: jobId,
                    customization_strength: 2
                })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to customize resume');
                }
                return response.json();
            })
            .then(data => {
                // Display results
                displayCustomizationResults(data);
                
                // Reload resumes to include the new customized version
                loadResumes();
            })
            .catch(error => {
                console.error('Error customizing resume:', error);
                showAlert('danger', 'Failed to customize resume. Please try again later.');
                resultsContainer.classList.add('d-none');
            })
            .finally(() => {
                // Re-enable button
                customizeBtn.disabled = false;
                customizeBtn.innerHTML = 'Customize Resume with AI';
            });
        });
    }
    
    // Generate Cover Letter
    if (coverLetterBtn) {
        coverLetterBtn.addEventListener('click', function() {
            const resumeId = selectResume.value;
            const jobId = selectJob.value;
            
            // Validate selection
            if (resumeId === 'Choose your resume...' || jobId === 'Choose a job description...') {
                showAlert('warning', 'Please select both a resume and a job description.');
                return;
            }
            
            // Show loading state
            coverLetterBtn.disabled = true;
            coverLetterBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Generating...';
            resultsContainer.innerHTML = '<div class="alert alert-info">Generating your cover letter with Claude AI. This may take a minute...</div><div class="d-flex justify-content-center"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div></div>';
            resultsContainer.classList.remove('d-none');
            
            // Send request to API
            fetch(`${API_BASE_URL}/cover-letter/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    resume_id: resumeId,
                    job_description_id: jobId,
                    tone: 'professional'
                })
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Failed to generate cover letter');
                }
                return response.json();
            })
            .then(data => {
                // Display results
                displayCoverLetterResults(data);
            })
            .catch(error => {
                console.error('Error generating cover letter:', error);
                showAlert('danger', 'Failed to generate cover letter. Please try again later.');
                resultsContainer.classList.add('d-none');
            })
            .finally(() => {
                // Re-enable button
                coverLetterBtn.disabled = false;
                coverLetterBtn.innerHTML = 'Generate Cover Letter';
            });
        });
    }
    
    // Display ATS analysis results
    function displayATSResults(data) {
        resultsContainer.innerHTML = `
            <div class="card">
                <div class="card-header">
                    <h4>ATS Compatibility Analysis</h4>
                </div>
                <div class="card-body">
                    <div class="mb-4">
                        <h5>Match Score</h5>
                        <div class="progress" style="height: 30px;">
                            <div class="progress-bar ${getScoreClass(data.match_score)}" role="progressbar" style="width: ${data.match_score}%;" aria-valuenow="${data.match_score}" aria-valuemin="0" aria-valuemax="100">${data.match_score}%</div>
                        </div>
                    </div>
                    
                    <div class="row mb-4">
                        <div class="col-md-6">
                            <h5>Matching Keywords</h5>
                            <ul class="list-group">
                                ${data.matching_keywords.map(kw => `
                                    <li class="list-group-item d-flex justify-content-between align-items-center">
                                        ${kw.keyword}
                                        <span class="badge bg-success rounded-pill">${kw.count_in_resume}x</span>
                                    </li>
                                `).join('')}
                            </ul>
                        </div>
                        <div class="col-md-6">
                            <h5>Missing Keywords</h5>
                            <ul class="list-group">
                                ${data.missing_keywords.map(kw => `
                                    <li class="list-group-item d-flex justify-content-between align-items-center">
                                        ${kw.keyword}
                                        <span class="badge bg-danger rounded-pill">${kw.count_in_job}x in job</span>
                                    </li>
                                `).join('')}
                            </ul>
                        </div>
                    </div>
                    
                    <div class="mb-4">
                        <h5>Improvement Suggestions</h5>
                        <div class="accordion" id="improvementAccordion">
                            ${data.improvements.map((imp, index) => `
                                <div class="accordion-item">
                                    <h2 class="accordion-header" id="heading${index}">
                                        <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#collapse${index}" aria-expanded="false" aria-controls="collapse${index}">
                                            <span class="badge ${getPriorityClass(imp.priority)} me-2">Priority ${imp.priority}</span> ${imp.category}
                                        </button>
                                    </h2>
                                    <div id="collapse${index}" class="accordion-collapse collapse" aria-labelledby="heading${index}" data-bs-parent="#improvementAccordion">
                                        <div class="accordion-body">
                                            ${imp.suggestion}
                                        </div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    
                    <div class="d-grid gap-2">
                        <button id="ai-customize-suggestion" class="btn btn-success">Customize Resume with AI</button>
                    </div>
                </div>
            </div>
        `;
        
        // Add click event for suggestion button
        document.getElementById('ai-customize-suggestion').addEventListener('click', function() {
            customizeBtn.click();
        });
    }
    
    // Display customization results
    function displayCustomizationResults(data) {
        // Fetch the customized resume
        fetch(`${API_BASE_URL}/resumes/${data.customized_resume_id}`)
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to fetch customized resume');
            }
            return response.json();
        })
        .then(resume => {
            resultsContainer.innerHTML = `
                <div class="card">
                    <div class="card-header">
                        <h4>Resume Customization Results</h4>
                    </div>
                    <div class="card-body">
                        <div class="alert alert-success">
                            <h5>Success!</h5>
                            <p>Your resume has been customized for the job description.</p>
                        </div>
                        
                        <div class="mb-4">
                            <h5>Customized Resume</h5>
                            <div class="card">
                                <div class="card-body bg-dark">
                                    <pre class="mb-0"><code>${resume.current_version.content}</code></pre>
                                </div>
                            </div>
                        </div>
                        
                        <div class="d-grid gap-2">
                            <a href="${API_BASE_URL}/export/resume/${data.customized_resume_id}/pdf" class="btn btn-primary" target="_blank">Download as PDF</a>
                            <a href="${API_BASE_URL}/export/resume/${data.customized_resume_id}/docx" class="btn btn-secondary" target="_blank">Download as DOCX</a>
                            <a href="${API_BASE_URL}/export/resume/${data.customized_resume_id}/markdown" class="btn btn-outline-secondary" target="_blank">Download as Markdown</a>
                        </div>
                    </div>
                </div>
            `;
        })
        .catch(error => {
            console.error('Error fetching customized resume:', error);
            showAlert('danger', 'Failed to fetch customized resume. Please try again later.');
        });
    }
    
    // Display cover letter results
    function displayCoverLetterResults(data) {
        resultsContainer.innerHTML = `
            <div class="card">
                <div class="card-header">
                    <h4>Cover Letter Generation Results</h4>
                </div>
                <div class="card-body">
                    <div class="alert alert-success">
                        <h5>Success!</h5>
                        <p>Your cover letter has been generated.</p>
                    </div>
                    
                    <div class="mb-4">
                        <h5>Generated Cover Letter</h5>
                        <div class="card">
                            <div class="card-body bg-dark">
                                <pre class="mb-0"><code>${data.cover_letter_content}</code></pre>
                            </div>
                        </div>
                    </div>
                    
                    <div class="d-grid gap-2">
                        <a href="${API_BASE_URL}/export/cover-letter/${data.resume_id}/${data.job_description_id}/pdf?content=${encodeURIComponent(data.cover_letter_content)}" class="btn btn-primary" target="_blank">Download as PDF</a>
                        <a href="${API_BASE_URL}/export/cover-letter/${data.resume_id}/${data.job_description_id}/docx?content=${encodeURIComponent(data.cover_letter_content)}" class="btn btn-secondary" target="_blank">Download as DOCX</a>
                        <a href="${API_BASE_URL}/export/cover-letter/${data.resume_id}/${data.job_description_id}/markdown?content=${encodeURIComponent(data.cover_letter_content)}" class="btn btn-outline-secondary" target="_blank">Download as Markdown</a>
                    </div>
                </div>
            </div>
        `;
    }
    
    // Helper function to get score class
    function getScoreClass(score) {
        if (score >= 80) return 'bg-success';
        if (score >= 60) return 'bg-primary';
        if (score >= 40) return 'bg-warning';
        return 'bg-danger';
    }
    
    // Helper function to get priority class
    function getPriorityClass(priority) {
        if (priority === 1) return 'bg-danger';
        if (priority === 2) return 'bg-warning';
        return 'bg-info';
    }
    
    // Helper function to show alerts
    function showAlert(type, message) {
        const alertsContainer = document.createElement('div');
        alertsContainer.className = 'alert-container position-fixed top-0 end-0 p-3';
        alertsContainer.style.zIndex = '5000';
        
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        
        alertsContainer.appendChild(alert);
        document.body.appendChild(alertsContainer);
        
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
            
            // Remove alert container after animation
            alert.addEventListener('closed.bs.alert', () => {
                if (alertsContainer.parentNode) {
                    document.body.removeChild(alertsContainer);
                }
            });
        }, 5000);
    }
});