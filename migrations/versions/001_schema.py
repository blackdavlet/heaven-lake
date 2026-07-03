from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '001'
down_revision = None
branch_labels = None

def upgrade() -> None:
    op.create_table(
        'videos',
        sa.Column('video_id', UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('filename', sa.Text, nullable=True),
        sa.Column('status', sa.Text, nullable=False, server_default='pending'),
        sa.Column('created_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.TIMESTAMP, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('chunk_count', sa.Integer, nullable=True)
    )


def downgrade() -> None:
    op.drop_table('processed_videos')
    op.drop_table('video_chunks')
    op.drop_table('videos')


