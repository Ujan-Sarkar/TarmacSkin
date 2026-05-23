import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { format } from 'date-fns';
import { CheckCircle2, Link, Clock } from 'lucide-react';

interface WorkorderCreatedProps {
  timestamp: Date;
  workorderId: string;
  onChainHash: string;
  status: 'active' | 'completed' | 'pending';
}

export function WorkorderCreated({ timestamp, workorderId, onChainHash, status }: WorkorderCreatedProps) {
  const getStatusColor = (currentStatus: string) => {
    switch (currentStatus) {
      case 'active':
        return 'bg-success text-success-foreground';
      case 'completed':
        return 'bg-primary text-primary-foreground'; // Or another suitable color
      case 'pending':
        return 'bg-warning text-warning-foreground';
      default:
        return 'bg-secondary text-secondary-foreground';
    }
  };

  return (
    <Card className="border-l-4 border-l-primary animate-in fade-in-0 duration-500">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-primary">
          <CheckCircle2 className="h-5 w-5" />
          Workorder Created
        </CardTitle>
        <CardDescription>Details of the recently generated work order.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Clock className="h-4 w-4" />
            <span>Timestamp:</span>
          </div>
          <span className="font-semibold">{format(timestamp, 'PPPpp')}</span>
        </div>

        <div className="flex items-center justify-between text-sm">
          <div className="text-muted-foreground">Workorder ID:</div>
          <span className="font-semibold font-mono">{workorderId}</span>
        </div>

        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2 text-muted-foreground">
            <Link className="h-4 w-4" />
            <span>On-Chain Hash:</span>
          </div>
          <span className="font-semibold font-mono truncate max-w-[200px] sm:max-w-none">
            {onChainHash}
          </span>
        </div>

        <div className="flex items-center justify-between text-sm">
          <div className="text-muted-foreground">Status:</div>
          <Badge className={`${getStatusColor(status)} capitalize`}>{status}</Badge>
        </div>
      </CardContent>
    </Card>
  );
}