"""sssync — a scriptable playlist sync tool for Qobuz, Spotify, and Jellyfin."""

import click

from . import __version__
from . import config as config_mod
from .exceptions import SssyncError
from .ui import spinner


@click.group()
@click.version_option(__version__, prog_name="sssync")
def main():
    """sssync — sync playlists and favorites between music services."""


@main.command()
@click.argument("source")
@click.argument("dest")
@click.argument("playlist", required=False)
@click.option("--name", "-n", default=None, help="Destination playlist name")
@click.option("--all", "sync_all", is_flag=True, help="Sync every playlist from SOURCE")
@click.option("--dry-run", is_flag=True, help="Show what would happen, change nothing")
def sync(source, dest, playlist, name, sync_all, dry_run):
    """Sync a playlist from SOURCE to DEST.

    PLAYLIST can be a name, an id, or a URL. Omit it with --all.

    Examples:

    \b
        sssync sync spotify qobuz "My Playlist"
        sssync sync qobuz jellyfin <playlist-id>
        sssync sync qobuz jellyfin <playlist-id> "My Playlist"
        sssync sync spotify qobuz --all
    """
    if source == dest:
        raise click.ClickException("SOURCE and DEST must differ")
    if not playlist and not sync_all:
        raise click.ClickException("Provide PLAYLIST or use --all")
    from .sync import sync_playlist

    try:
        cfg = config_mod.load()
        with spinner(f"authenticating {source}…"):
            src = config_mod.make_source(cfg, source)
        with spinner(f"authenticating {dest}…"):
            dst = config_mod.make_source(cfg, dest)
    except SssyncError as e:
        raise click.ClickException(str(e))

    try:
        if sync_all:
            playlists = src.list_playlists()
            click.echo(f"Syncing {len(playlists)} playlists {source} → {dest}")
            for p in playlists:
                r = sync_playlist(src, dst, p.source_id, p.name, dry_run, is_id=True)
                click.echo(r.summary())
        else:
            r = sync_playlist(src, dst, playlist, name, dry_run)
            click.echo(r.summary())
    except SssyncError as e:
        raise click.ClickException(str(e))


@main.command("favorites")
@click.argument("source")
@click.argument("dest")
@click.option("--dry-run", is_flag=True)
def favorites(source, dest, dry_run):
    """Sync SOURCE favorites (liked tracks) into DEST favorites."""
    try:
        cfg = config_mod.load()
        src = config_mod.make_source(cfg, source)
        dst = config_mod.make_source(cfg, dest)
    except SssyncError as e:
        raise click.ClickException(str(e))

    try:
        src_tracks = src.get_favorite_tracks()
    except NotImplementedError:
        raise click.ClickException(f"{source} does not support favorites")
    existing = {
        (t.title.lower(), t.artist.lower()) for t in dst.get_favorite_tracks()
    }

    missing = [
        t for t in src_tracks
        if (t.title.lower(), t.artist.lower()) not in existing
    ]
    click.echo(f"{len(missing)} of {len(src_tracks)} favorites not in {dest}")
    if dry_run or not missing:
        return

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
    try:
        cfg = config_mod.load()
        with spinner(f"authenticating {source}…"):
            src = config_mod.make_source(cfg, source)
        with spinner("fetching playlists…"):
            playlists = src.list_playlists()
    except SssyncError as e:
        raise click.ClickException(str(e))
    for p in playlists:
        count = str(p.track_count) if p.track_count else "-"
        click.echo(f"{p.source_id}\t{count:>5}\t{p.name}")


@main.command()
def config():
    """Open the config file (creates a default one first)."""
    import os

    path = config_mod.ensure_config()
    editor = os.environ.get("EDITOR", "vi")
    os.execvp(editor, [editor, str(path)])


if __name__ == "__main__":
    main()
