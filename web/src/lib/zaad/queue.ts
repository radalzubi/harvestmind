/**
 * How many runs a queued job is waiting behind: the solves holding the planner now plus the queued
 * runs ahead of it. Null when the server does not say (an older server, or a job it is not holding).
 * The planner runs one solve at a time, in submission order; this is what the queued state shows.
 */
export function queueAheadOf(job: { status: string; queue_position?: number | null; running_now?: number }): number | null {
  if (job.status !== "QUEUED" || job.queue_position == null) return null;
  return Math.max(0, job.queue_position - 1) + (job.running_now ?? 0);
}
