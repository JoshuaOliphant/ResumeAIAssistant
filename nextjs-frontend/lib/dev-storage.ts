"use client"

import { Resume, ResumeVersion, JobDescription } from "./client";

// Check if we're in the browser environment
const isBrowser = typeof window !== 'undefined';

// Dev Storage Keys
const DEV_RESUMES_KEY = 'dev_resumes';
const DEV_JOBS_KEY = 'dev_jobs';

// Helper function to generate IDs
const generateId = () => Math.random().toString(36).substring(2, 9);

// Helper function to get the current timestamp
const getCurrentTimestamp = () => new Date().toISOString();

// Get all resumes from localStorage
export const getResumes = (): Resume[] => {
  if (!isBrowser) return [];
  
  try {
    const resumes = localStorage.getItem(DEV_RESUMES_KEY);
    return resumes ? JSON.parse(resumes) : [];
  } catch (error) {
    console.error('Error retrieving resumes from localStorage:', error);
    return [];
  }
};

// Save resumes to localStorage
export const saveResumes = (resumes: Resume[]) => {
  if (!isBrowser) return;
  
  try {
    localStorage.setItem(DEV_RESUMES_KEY, JSON.stringify(resumes));
  } catch (error) {
    console.error('Error saving resumes to localStorage:', error);
  }
};

// Get a single resume by ID
export const getResumeById = (id: string): Resume | undefined => {
  return getResumes().find(resume => resume.id === id);
};

// Create a new resume
export const createResume = (data: { title: string; content: string }): Resume => {
  const resumes = getResumes();
  
  const timestamp = getCurrentTimestamp();
  const resumeId = generateId();
  const versionId = generateId();
  
  // Create resume version
  const version: ResumeVersion = {
    id: versionId,
    resume_id: resumeId,
    content: data.content,
    version_number: 1,
    is_customized: false,
    created_at: timestamp,
  };
  
  // Create resume
  const newResume: Resume = {
    id: resumeId,
    title: data.title,
    created_at: timestamp,
    updated_at: timestamp,
    current_version: version,
  };
  
  // Save to localStorage
  saveResumes([...resumes, newResume]);
  
  return newResume;
};

// Update an existing resume
export const updateResume = (id: string, updates: { title?: string; content?: string }): Resume => {
  const resumes = getResumes();
  const resumeIndex = resumes.findIndex(resume => resume.id === id);
  
  if (resumeIndex === -1) {
    throw new Error(`Resume with ID ${id} not found`);
  }
  
  const updatedResume = { ...resumes[resumeIndex] };
  const timestamp = getCurrentTimestamp();
  
  // Update title if provided
  if (updates.title) {
    updatedResume.title = updates.title;
  }
  
  // Update content if provided
  if (updates.content) {
    // Create a new version
    const versionId = generateId();
    const newVersion: ResumeVersion = {
      id: versionId,
      resume_id: id,
      content: updates.content,
      version_number: updatedResume.current_version.version_number + 1,
      is_customized: false,
      created_at: timestamp,
    };
    
    updatedResume.current_version = newVersion;
  }
  
  updatedResume.updated_at = timestamp;
  
  // Update the resumes array
  resumes[resumeIndex] = updatedResume;
  saveResumes(resumes);
  
  return updatedResume;
};

// Delete a resume
export const deleteResume = (id: string): void => {
  const resumes = getResumes().filter(resume => resume.id !== id);
  saveResumes(resumes);
};

// Get all job descriptions from localStorage
export const getJobs = (): JobDescription[] => {
  if (!isBrowser) return [];
  
  try {
    const jobs = localStorage.getItem(DEV_JOBS_KEY);
    return jobs ? JSON.parse(jobs) : [];
  } catch (error) {
    console.error('Error retrieving jobs from localStorage:', error);
    return [];
  }
};

// Save job descriptions to localStorage
export const saveJobs = (jobs: JobDescription[]) => {
  if (!isBrowser) return;
  
  try {
    localStorage.setItem(DEV_JOBS_KEY, JSON.stringify(jobs));
  } catch (error) {
    console.error('Error saving jobs to localStorage:', error);
  }
};

// Get a single job description by ID
export const getJobById = (id: string): JobDescription | undefined => {
  return getJobs().find(job => job.id === id);
};

// Create a new job description
export const createJob = (data: { title: string; company?: string; description: string }): JobDescription => {
  const jobs = getJobs();
  
  const timestamp = getCurrentTimestamp();
  const jobId = generateId();
  
  // Create job description
  const newJob: JobDescription = {
    id: jobId,
    title: data.title,
    company: data.company,
    description: data.description,
    created_at: timestamp,
    updated_at: timestamp,
  };
  
  // Save to localStorage
  saveJobs([...jobs, newJob]);
  
  return newJob;
};

// Update an existing job description
export const updateJob = (id: string, updates: { title?: string; company?: string; description?: string }): JobDescription => {
  const jobs = getJobs();
  const jobIndex = jobs.findIndex(job => job.id === id);
  
  if (jobIndex === -1) {
    throw new Error(`Job description with ID ${id} not found`);
  }
  
  const updatedJob = { 
    ...jobs[jobIndex],
    ...updates,
    updated_at: getCurrentTimestamp(),
  };
  
  // Update the jobs array
  jobs[jobIndex] = updatedJob;
  saveJobs(jobs);
  
  return updatedJob;
};

// Delete a job description
export const deleteJob = (id: string): void => {
  const jobs = getJobs().filter(job => job.id !== id);
  saveJobs(jobs);
};