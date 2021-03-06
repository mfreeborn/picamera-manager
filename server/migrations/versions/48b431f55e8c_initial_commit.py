"""initial commit

Revision ID: 48b431f55e8c
Revises: 
Create Date: 2021-04-12 11:09:49.203583

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '48b431f55e8c'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('registered_cameras',
    sa.Column('camera_id', sa.Integer(), nullable=False),
    sa.Column('ip_address', sa.Text(), nullable=False),
    sa.Column('port', sa.Text(), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('youtube_stream_id', sa.Text(), nullable=True),
    sa.Column('youtube_broadcast_id', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('camera_id'),
    sa.UniqueConstraint('ip_address'),
    sa.UniqueConstraint('name')
    )
    op.create_table('media',
    sa.Column('media_id', sa.Integer(), nullable=False),
    sa.Column('camera_id', sa.Integer(), nullable=False),
    sa.Column('media_type', sa.Text(), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=False),
    sa.Column('file_stem', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['camera_id'], ['registered_cameras.camera_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('media_id')
    )
    op.create_table('motion_videos',
    sa.Column('video_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['video_id'], ['media.media_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('video_id')
    )
    op.create_table('timelapse_images',
    sa.Column('image_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['image_id'], ['media.media_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('image_id')
    )
    op.create_table('timelapse_videos',
    sa.Column('video_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['video_id'], ['media.media_id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('video_id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('timelapse_videos')
    op.drop_table('timelapse_images')
    op.drop_table('motion_videos')
    op.drop_table('media')
    op.drop_table('registered_cameras')
    # ### end Alembic commands ###
