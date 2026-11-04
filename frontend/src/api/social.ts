import { apiClient } from "./client";
import { GameName } from "./games";

export interface Friend {
  id: string;
  full_name: string;
  username: string | null;
  programme: string | null;
  xp: number;
}

export interface FriendRequest {
  request_id: string;
  user: Friend;
}

export interface FriendsOverview {
  friends: Friend[];
  incoming: FriendRequest[];
  outgoing: FriendRequest[];
}

export type LeaderboardScope = "friends" | "programme";
export type LeaderboardPeriod = "week" | "all";

export interface Standing {
  rank: number;
  student_id: string;
  name: string;
  username: string | null;
  programme: string | null;
  xp: number;
  is_me: boolean;
}

export interface Leaderboard {
  scope: LeaderboardScope;
  period: LeaderboardPeriod;
  programme: string | null;
  /** Whether you have opted into the programme board. */
  joined: boolean;
  standings: Standing[];
}

export interface Challenge {
  id: string;
  game: GameName;
  game_name: string;
  title: string;
  direction: "sent" | "received";
  other: Friend | null;
  my_score: number | null;
  their_score: number | null;
  status: "open" | "completed" | "expired";
  outcome: "won" | "lost" | "draw" | null;
  expires_at: string;
  created_at: string;
}

export async function getFriends(): Promise<FriendsOverview> {
  const { data } = await apiClient.get<FriendsOverview>("/friends");
  return data;
}

export async function sendFriendRequest(username: string): Promise<void> {
  await apiClient.post("/friends/requests", { username });
}

export async function acceptFriendRequest(requestId: string): Promise<void> {
  await apiClient.post(`/friends/requests/${requestId}/accept`);
}

export async function declineFriendRequest(requestId: string): Promise<void> {
  await apiClient.post(`/friends/requests/${requestId}/decline`);
}

export async function removeFriend(userId: string): Promise<void> {
  await apiClient.delete(`/friends/${userId}`);
}

export async function getLeaderboard(scope: LeaderboardScope, period: LeaderboardPeriod): Promise<Leaderboard> {
  const { data } = await apiClient.get<Leaderboard>("/leaderboard", { params: { scope, period } });
  return data;
}

export async function getProgrammes(): Promise<string[]> {
  const { data } = await apiClient.get<string[]>("/programmes");
  return data;
}

export async function listChallenges(): Promise<Challenge[]> {
  const { data } = await apiClient.get<Challenge[]>("/challenges");
  return data;
}

export async function createChallenges(roundId: string, friendIds: string[]): Promise<Challenge[]> {
  const { data } = await apiClient.post<Challenge[]>("/challenges", { round_id: roundId, friend_ids: friendIds });
  return data;
}
