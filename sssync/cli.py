"""sssync — a scriptable playlist sync tool for Qobuz, Spotify, and Jellyfin."""

import sys

import click

from . import __version__
from . import config as config_mod


@click.group()
@click.version_option(__version__, prog_name="sssync")
def main():
    """sssync — sync playlists and favorites between music services."""


@main.command()
@click.argument("source")
@click.argument("dest")
@click.argument("playlist")
@click.option("--name", "-n", default=None, help="Destination playlist name")
@click.option("--all", "sync_all", is_flag=True, help="Sync every playlist from SOURCE")
@click.option("--dry-run", is_flag=True, help="Show what would happen, change nothing")
def sync(source, dest, playlist, name, sync_all, dry_run):
    """Sync a playlist from SOURCE to DEST.

    PLAYLIST can be a name, an id, or a URL.

    Examples:

    \b
        sssync sync spotify qobuz "My Playlist"
        sssync sync qobuz jellyfin <playlist-id>
        sssync sync qobuz jellyfin <playlist-id> "My Playlist"
        sssync sync spotify qobuz --all
    """
    if source == dest:
        raise click.ClickException("SOURCE and DEST must differ")
    cfg = config_mod.load()
    src = config_mod.make_source(cfg, source)
    dst = config_mod.make_source(cfg, dest)

    from .sync import sync_playlist

    if sync_all:
        playlists = src.list_playlists()
        click.echo(f"Syncing {len(playlists)} playlists {source} → {dest}")
        for p in playlists:
            r = sync_playlist(src, dst, p.source_id, p.name, dry_run)
            click.echo(r.summary())
    else:
        r = sync_playlist(src, dst, playlist, name, dry_run)
        click.echo(r.summary())


@main.command("favorites")
@click.argument("source")
@click.argument("dest")
@click.option("--dry-run", is_flag=True)
def favorites(source, dest, dry_run):
    """Sync SOURCE favorites (liked tracks) into DEST favorites."""
    cfg = config_mod.load()
    src = config_mod.make_source(cfg, source)
    dst = config_mod.make_source(cfg, dest)

    try:
        src_tracks = src.get_favorite_tracks()
    except NotImplementedError:
        raise click.ClickException(f"{source} does not support favorites")
    existing = {t.source_id for t in dst.get_favorite_tracks()}

    from .matcher import best_match
    from .sync import resolve_tracks

    missing = [t for t in src_tracks if t.source_id not in existing]
    click.echo(f"{len(missing)} of {len(src_tracks)} favorites not in {dest}")
    if dry_run or not missing:
        return

    # favorites need native ids — search for each
    added = 0
    for t in missing:
        hit = dst.search_track(t)
        if hit and dst.add_favorite_track(hit):
            added += 1
    click.echo(f"Added {added} favorites to {dest}")


@main.command()
@click.argument("source")
def playlists(source):
    """List playlists on a SOURCE."""
    cfg = config_mod.load()
    src = config_mod.make_source(cfg, source)
    for p in src.list_playlists():
        click.echo(f"{p.source_id}\t{p.track_count:>5}\t{p.name}")


@main.command()
def config():
    """Open the config file (creates a default one first)."""
    import os

    path = config_mod.ensure_config()
    editor = os.environ.get("EDITOR", "vi")
    os.execvp(editor, [editor, str(path)])


if __name__ == "__main__":
    main()
