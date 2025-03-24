"use client"

import { useState } from "react"
import { JobDescription, JobService } from "@/lib/client"
import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination"
import { Edit, Trash2, Calendar, Building, ExternalLink, Search } from "lucide-react"
import { useRouter } from "next/navigation"
import Link from "next/link"

interface JobsTableProps {
  jobs: JobDescription[]
  onChange: () => void
  onSelect?: (jobId: string) => void
}

export function JobsTable({ jobs, onChange, onSelect }: JobsTableProps) {
  const router = useRouter()
  const [sortBy, setSortBy] = useState<"date" | "title" | "company">("date")
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc")
  const [confirmDelete, setConfirmDelete] = useState<JobDescription | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)
  const [searchTerm, setSearchTerm] = useState("")
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 5

  // Filter jobs by search term
  const filteredJobs = jobs.filter(job => 
    job.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (job.company && job.company.toLowerCase().includes(searchTerm.toLowerCase())) ||
    job.description.toLowerCase().includes(searchTerm.toLowerCase())
  )

  // Sort filtered jobs
  const sortedJobs = [...filteredJobs].sort((a, b) => {
    if (sortBy === "date") {
      return sortOrder === "asc" 
        ? new Date(a.updated_at).getTime() - new Date(b.updated_at).getTime()
        : new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
    } else if (sortBy === "company") {
      const companyA = a.company || "";
      const companyB = b.company || "";
      return sortOrder === "asc"
        ? companyA.localeCompare(companyB)
        : companyB.localeCompare(companyA)
    } else {
      return sortOrder === "asc"
        ? a.title.localeCompare(b.title)
        : b.title.localeCompare(a.title)
    }
  })

  // Calculate pagination
  const totalPages = Math.ceil(sortedJobs.length / itemsPerPage)
  const paginatedJobs = sortedJobs.slice(
    (currentPage - 1) * itemsPerPage,
    currentPage * itemsPerPage
  )

  const toggleSort = (column: "date" | "title" | "company") => {
    if (sortBy === column) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc")
    } else {
      setSortBy(column)
      setSortOrder("asc")
    }
  }

  const handleEdit = (jobId: string) => {
    router.push(`/jobs/${jobId}`)
  }

  const handleSelect = (jobId: string) => {
    if (onSelect) {
      onSelect(jobId)
    }
  }

  const handleDelete = async () => {
    if (!confirmDelete) return

    try {
      setIsDeleting(true)
      await JobService.deleteJob(confirmDelete.id)
      onChange()
    } catch (error) {
      console.error("Error deleting job:", error)
    } finally {
      setIsDeleting(false)
      setConfirmDelete(null)
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric"
    })
  }

  // Generate pagination items
  const renderPaginationItems = () => {
    const items = []
    
    // Always show first page
    items.push(
      <PaginationItem key="page-1">
        <PaginationLink 
          onClick={() => setCurrentPage(1)}
          isActive={currentPage === 1}
        >
          1
        </PaginationLink>
      </PaginationItem>
    )
    
    // Show ellipsis if needed
    if (currentPage > 3) {
      items.push(
        <PaginationItem key="ellipsis-1">
          <PaginationLink disabled>...</PaginationLink>
        </PaginationItem>
      )
    }
    
    // Show current page and surrounding pages
    for (let i = Math.max(2, currentPage - 1); i <= Math.min(totalPages - 1, currentPage + 1); i++) {
      if (i === 1 || i === totalPages) continue // Skip first and last pages as they're always shown
      items.push(
        <PaginationItem key={`page-${i}`}>
          <PaginationLink 
            onClick={() => setCurrentPage(i)}
            isActive={currentPage === i}
          >
            {i}
          </PaginationLink>
        </PaginationItem>
      )
    }
    
    // Show ellipsis if needed
    if (currentPage < totalPages - 2 && totalPages > 3) {
      items.push(
        <PaginationItem key="ellipsis-2">
          <PaginationLink disabled>...</PaginationLink>
        </PaginationItem>
      )
    }
    
    // Always show last page if there is more than one page
    if (totalPages > 1) {
      items.push(
        <PaginationItem key={`page-${totalPages}`}>
          <PaginationLink 
            onClick={() => setCurrentPage(totalPages)}
            isActive={currentPage === totalPages}
          >
            {totalPages}
          </PaginationLink>
        </PaginationItem>
      )
    }
    
    return items
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="relative max-w-sm">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            type="search"
            placeholder="Search jobs..."
            className="pl-8"
            value={searchTerm}
            onChange={e => {
              setSearchTerm(e.target.value)
              setCurrentPage(1) // Reset to first page on search
            }}
          />
        </div>
        <Button asChild variant="default">
          <Link href="/jobs/new">
            Create New Job
          </Link>
        </Button>
      </div>

      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead 
                className="cursor-pointer"
                onClick={() => toggleSort("title")}
              >
                Title {sortBy === "title" && (sortOrder === "asc" ? "↑" : "↓")}
              </TableHead>
              <TableHead 
                className="cursor-pointer"
                onClick={() => toggleSort("company")}
              >
                Company {sortBy === "company" && (sortOrder === "asc" ? "↑" : "↓")}
              </TableHead>
              <TableHead 
                className="cursor-pointer"
                onClick={() => toggleSort("date")}
              >
                Last Updated {sortBy === "date" && (sortOrder === "asc" ? "↑" : "↓")}
              </TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {paginatedJobs.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} className="text-center text-muted-foreground">
                  {sortedJobs.length === 0 
                    ? "No job descriptions found. Create a new job description to get started."
                    : "No matching job descriptions found."}
                </TableCell>
              </TableRow>
            ) : (
              paginatedJobs.map((job) => (
                <TableRow key={job.id}>
                  <TableCell className="font-medium">
                    <div className="flex items-center">
                      <span 
                        className="hover:underline cursor-pointer"
                        onClick={() => handleSelect(job.id)}
                      >
                        {job.title}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>
                    {job.company ? (
                      <div className="flex items-center">
                        <Building className="h-4 w-4 mr-2 text-muted-foreground" />
                        {job.company}
                      </div>
                    ) : (
                      <span className="text-muted-foreground text-sm">Not specified</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center">
                      <Calendar className="h-4 w-4 mr-2 text-muted-foreground" />
                      {formatDate(job.updated_at)}
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      <Button
                        variant="ghost" 
                        size="icon"
                        onClick={() => handleSelect(job.id)}
                        title="Select Job"
                      >
                        <ExternalLink className="h-4 w-4" />
                        <span className="sr-only">Select</span>
                      </Button>
                      <Button
                        variant="ghost" 
                        size="icon"
                        onClick={() => handleEdit(job.id)}
                        title="Edit Job"
                      >
                        <Edit className="h-4 w-4" />
                        <span className="sr-only">Edit</span>
                      </Button>
                      <Button
                        variant="ghost" 
                        size="icon"
                        onClick={() => setConfirmDelete(job)}
                        title="Delete Job"
                      >
                        <Trash2 className="h-4 w-4" />
                        <span className="sr-only">Delete</span>
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <Pagination>
          <PaginationContent>
            <PaginationItem>
              <PaginationPrevious 
                onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                aria-disabled={currentPage === 1}
                tabIndex={currentPage === 1 ? -1 : 0}
                className={currentPage === 1 ? "pointer-events-none opacity-50" : ""}
              />
            </PaginationItem>
            
            {renderPaginationItems()}
            
            <PaginationItem>
              <PaginationNext 
                onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                aria-disabled={currentPage === totalPages}
                tabIndex={currentPage === totalPages ? -1 : 0}
                className={currentPage === totalPages ? "pointer-events-none opacity-50" : ""}
              />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      )}

      <div className="text-sm text-muted-foreground">
        {filteredJobs.length} {filteredJobs.length === 1 ? "job description" : "job descriptions"}
        {filteredJobs.length !== jobs.length && ` (filtered from ${jobs.length})`}
      </div>

      <Dialog open={!!confirmDelete} onOpenChange={(open) => !open && setConfirmDelete(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Job Description</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete &quot;{confirmDelete?.title}&quot;? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setConfirmDelete(null)}
              disabled={isDeleting}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={isDeleting}
            >
              {isDeleting ? "Deleting..." : "Delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}