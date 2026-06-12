import { Avatar } from '@/shared/ui'
import { fullName } from '@/shared/lib/format'
import type { Comment } from '../model/types'

export function CommentItem({ comment }: { comment: Comment }) {
  return (
    <div className="comment">
      <Avatar name={comment.author.first_name} src={comment.author.avatar_url} size="tiny" />
      <div className="comment__content">
        <span className="comment__author">{fullName(comment.author)}</span>
        <span className="comment__text">{comment.content}</span>
      </div>
    </div>
  )
}
