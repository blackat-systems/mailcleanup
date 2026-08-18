export type Evidence = {
  code: string;
  label: string;
  detail: string;
  strength: string;
};

export type MessageRecord = {
  id: string;
  threadId: string;
  receivedAt: string;
  senderName: string;
  senderEmail: string;
  subject: string;
  labels: string[];
  gmailCategory: string;
  sourceId: string;
  sourceName: string;
  sourceAmbiguous: boolean;
  rubro: string;
  intencion: string;
  suscripcion: string;
  proteccion: string;
  confianza: string;
  metodoBaja: string;
  recomendacion: string;
  protected: boolean;
  sizeBytes: number;
  failureState: string | null;
  fixtureTags: string[];
  revision: number;
  evidence: Evidence[];
};

export type FlowRecord = {
  id: string;
  name: string;
  messageCount: number;
  protectedCount: number;
  subscriptionStates: string[];
};

export type SourceRecord = {
  id: string;
  name: string;
  messageCount: number;
  unreadCount: number;
  protectedCount: number;
  candidateCount: number;
  totalBytes: number;
  firstSeen: string;
  lastSeen: string;
  senders: string[];
  domains: string[];
  rubro: string;
  rubros: Record<string, number>;
  dominantIntent: string;
  intents: Record<string, number>;
  subscription: string;
  subscriptionStates: Record<string, number>;
  unsubscribeMethods: Record<string, number>;
  confidence: string;
  ambiguous: boolean;
  isSpam: boolean;
  isSubscription: boolean;
  recommendation: string;
  flows: FlowRecord[];
  evidence: Evidence[];
  recentMessages: MessageRecord[];
};

export type Dashboard = {
  mode: "synthetic";
  snapshotAt: string;
  totalMessages: number;
  totalSources: number;
  subscriptionSources: number;
  spamMessages: number;
  protectedMessages: number;
  candidateMessages: number;
  totalBytes: number;
  rubros: { name: string; count: number }[];
  topSources: SourceRecord[];
  fixtureCoverage: { covered: number; required: number; missing: string[] };
};

export type AnalysisStatus = {
  mode: "synthetic";
  state: string;
  phases: { name: string; state: string }[];
  incidents: { messageId: string; state: string; resolution: string }[];
};

export type Configuration = {
  mode: "synthetic";
  platform: string;
  experience: string;
  timezone: string;
  protectedLabels: string[];
  schemaVersion: number;
  gmailConnected: boolean;
  oauthAvailable: boolean;
  remoteAi: boolean;
  permanentDelete: boolean;
};

export type PlanRequest = {
  sourceIds: string[];
  beforeDate: string | null;
  keepLatest: number;
  operations: ("trash" | "archive" | "unsubscribe")[];
};

export type PlanPreview = {
  id: string;
  createdAt: string;
  status: string;
  selection: PlanRequest & { timezone: string };
  sourceCount: number;
  messageCount: number;
  totalBytes: number;
  excludedCount: number;
  exclusions: { messageId: string; reason: string }[];
  sample: MessageRecord[];
  warnings: string[];
  canExecute: false;
};

export type HistoryPlan = {
  id: string;
  createdAt: string;
  selection: PlanRequest & { timezone: string };
  snapshot: {
    messageCount: number;
    messages: { id: string; revision: number; sourceId: string; receivedAt: string }[];
    excludedCount: number;
    totalBytes: number;
  };
  status: string;
};
