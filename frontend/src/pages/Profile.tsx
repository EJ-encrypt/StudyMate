import { useAuth } from "../context/AuthContext";

export default function Profile() {
  const { user } = useAuth();

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="text-2xl font-bold text-navy">Profile</h1>
      <dl className="mt-4 grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-navy">
        <dt className="font-semibold">Name</dt>
        <dd>{user?.full_name}</dd>
        <dt className="font-semibold">Email</dt>
        <dd>{user?.email}</dd>
        <dt className="font-semibold">Role</dt>
        <dd className="capitalize">{user?.role}</dd>
      </dl>
      <p className="mt-6 text-navy/70">Streaks, XP, and badges land in Phase 6.</p>
    </div>
  );
}
