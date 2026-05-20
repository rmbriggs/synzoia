import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import {
  currentUserId,
  getUser,
  relativeTime,
  type ChatMessage as ChatMessageT,
} from '@/lib/mockData';

export default function ChatMessage({ message }: { message: ChatMessageT }) {
  const user = getUser(message.userId);
  if (!user) return null;
  const isMe = message.userId === currentUserId;

  return (
    <div
      className={`flex items-start gap-3 ${isMe ? 'flex-row-reverse text-right' : ''}`}
    >
      <Avatar className="shrink-0">
        <AvatarFallback>{user.initials}</AvatarFallback>
      </Avatar>
      <div className={`flex-1 min-w-0 max-w-md ${isMe ? 'ml-auto' : ''}`}>
        <div
          className={`flex items-baseline gap-2 ${isMe ? 'justify-end' : ''}`}
        >
          <span className="font-display italic text-sm">
            {isMe ? 'you' : user.displayName}
          </span>
          <span className="label-mono text-muted-foreground">
            {relativeTime(message.sentAt)}
          </span>
        </div>
        <div
          className={`mt-1 inline-block px-4 py-2 rounded-2xl border leading-relaxed ${
            isMe
              ? 'bg-primary text-primary-foreground border-primary rounded-br-sm'
              : 'bg-muted border-border rounded-bl-sm'
          }`}
        >
          {message.body}
        </div>
      </div>
    </div>
  );
}
