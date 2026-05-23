export interface WorkorderData {
  timestamp: Date;
  workorderId: string;
  onChainHash: string;
  status: 'active' | 'completed' | 'pending';
}