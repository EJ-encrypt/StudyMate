import { BookOpen, ChevronRight, FileText } from "lucide-react";
import { ReactNode } from "react";
import { Link } from "react-router-dom";

import { Course } from "../api/courses";

/** One course in a grid, linking wherever the current page sends it. */
export default function CourseCard({
  course,
  to,
  footer,
  disabled = false,
}: {
  course: Course;
  to: string;
  footer?: ReactNode;
  disabled?: boolean;
}) {
  const body = (
    <>
      <div className="flex items-start justify-between gap-2">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-navy/5 text-navy group-hover:bg-gold/20">
          <BookOpen className="h-[18px] w-[18px]" aria-hidden />
        </span>
        {!disabled && (
          <ChevronRight className="h-4 w-4 text-navy/30 transition group-hover:translate-x-0.5 group-hover:text-gold-dark" aria-hidden />
        )}
      </div>
      <p className="mt-3 text-sm font-bold text-navy">{course.code}</p>
      <p className="line-clamp-2 text-sm text-navy/70">{course.name}</p>
      <p className="mt-2 flex items-center gap-1 text-xs text-navy/50">
        {footer ?? (
          <>
            <FileText className="h-3.5 w-3.5" aria-hidden />
            {course.document_count === 0
              ? "No material yet"
              : `${course.document_count} file${course.document_count === 1 ? "" : "s"}`}
          </>
        )}
      </p>
    </>
  );

  if (disabled) {
    return <div className="card p-4 opacity-55">{body}</div>;
  }
  return (
    <Link to={to} className="card group p-4 transition hover:-translate-y-0.5 hover:border-gold hover:shadow-lift">
      {body}
    </Link>
  );
}
