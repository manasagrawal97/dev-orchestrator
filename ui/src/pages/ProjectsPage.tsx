import { useEffect, useState } from 'react';
import { devoApi } from '../api/client';
import { StatusBadge } from '../components/StatusBadge';
import type { ProjectSummary } from '../types/devo';

interface ProjectsPageProps {
  selectedProject: string | null;
  onSelectProject: (project: string) => void;
}

export function ProjectsPage({ selectedProject, onSelectProject }: ProjectsPageProps) {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setLoading(true);
    devoApi
      .getProjects()
      .then((data) => {
        if (active) {
          setProjects(data.projects);
          setError(null);
        }
      })
      .catch((err: Error) => {
        if (active) {
          setError(err.message);
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  if (loading) {
    return <p className="muted">Loading projects from the local Devo API...</p>;
  }

  if (error) {
    return <p className="error-text">{error}</p>;
  }

  if (!projects.length) {
    return <p className="muted">No registered projects found.</p>;
  }

  return (
    <section>
      <div className="section-heading">
        <h2>Projects</h2>
        <p>{projects.length} registered</p>
      </div>
      <div className="project-grid">
        {projects.map((project) => (
          <button
            className={`project-card ${project.name === selectedProject ? 'selected' : ''}`}
            key={project.name}
            type="button"
            onClick={() => onSelectProject(project.name)}
          >
            <span className="project-card-title">{project.name}</span>
            <StatusBadge status={project.path_exists ? 'OK' : 'FAIL'} />
            <span className="project-path">{project.path}</span>
          </button>
        ))}
      </div>
    </section>
  );
}
