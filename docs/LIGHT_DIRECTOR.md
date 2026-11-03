# Light Director: design

A light and pyro coordinator for the Main stage (and, later, the club and rooftop rigs). It works like a festival lighting designer with a pre-programmed show: the song is studied once, a cue timeline is written for it, and the timeline is played back in sync with the beat.

Status: design, not built yet. See the version log in [KNOWLEDGE.md](KNOWLEDGE.md) for progress.

## What is wrong today

- **Lights hold still.** The beam fixtures jump to a new spot on each beat and then hold. In quiet passages they step only once a bar. Several laser looks hold one pose for the whole bar.
- **Cues follow a formula, not the music.** Pyro and big lasers fire on a 4-bar grid inside "punchy" sections. They never look at what happens on a given beat. So they land on the right bar, but they can miss the real hits (a snare fill ending, the drop after a build) and fire on beats where nothing special happens.
- **No arc.** There's no build-up language: no rising strobe rate, no breath before the drop, no calm breakdown look. So the drop doesn't feel bigger than the rest.

## How professionals do it (research summary)

- **Phrasing first.** Festival shows are programmed around the track's phrases. Dance music runs 4 beats to a bar, 4 or 8 bars to a phrase, and 8 to 32 bars to a section: intro, build, drop, breakdown, second build, second drop, outro. Big changes land on phrase starts.
- **Timecode for headline sets.** The strongest shows are pre-programmed against a timeline (timecode), not improvised. Software like SoundSwitch does this automatically: it detects phrases (Intro, Main, Middle, Bridge, Outro), writes a script aligned to the beat grid, and falls back to generic "autoloops" when there's no script.
- **Builds have a language.** During a build, fixtures pulse at partial intensity on the snare hits. Strobe rate starts slow (tension) and speeds up towards the drop. The stage dims, or blacks out for a beat, just before the drop, so the first beat of the drop hits harder.
- **Restraint and contrast.** Flashing everything on every beat is tiring. The big gestures (blinders, strobe, pyro, a fast mover sweep) are saved for the drops. Calmer looks in between make the next peak land. Every drop gets its own signature, for example the first drop on strobe and blinders and the second on a fast sweep. Never black out completely for long, for crowd safety.
- **What marks EDM sections in the audio.** Not chords or vocals, but spectral brightness, rhythmic density and low-frequency (bass) energy.
  - **Build:** rising brightness and density with the bass thinning out.
  - **Drop:** the bass and overall energy come back at full strength right after a build or a break.
  - **Detectors:** energy novelty, drum-onset counts and spectral flux are the strongest boundary signals. Simple detectors weight energy flux and bass flux most.

## Design

Two parts: an analyser that runs once per song in the existing beat worker, and a director that runs every frame and is cheap.

### 1. Song analysis (offline, in the worker)

The existing `songAnalysis` pass already computes onset flux, low-band flux, RMS, the beat grid, the downbeat and quiet (`chill`) beats. It is extended to return a **show map**.

**Per-beat features** (already mostly computed, now kept):

| Feature | Meaning |
|---|---|
| `kick[i]` | low-band onset strength at the beat |
| `snare[i]` | mid/high onset strength at the beat, plus half-beat (8th) onsets for rolls |
| `loud[i]` | RMS over the beat |
| `bright[i]` | spectral brightness: the high-band share of the energy |
| `dens[i]` | onset density: onsets per beat, counting off-beats |

**Per-bar summaries:**

- **`energy[b]`:** a 0..1 bar energy, normalised per song, from loudness x bass x density.
- **Novelty:** the change between neighbouring bars in (energy, bass, brightness, density).

**Sections:**

- **Boundaries:** novelty peaks, snapped to the 4- or 8-bar grid from the downbeat. Minimum section length 4 bars.
- **Labels**, by rules on the section's features:
  - **intro:** the first section, before full bass;
  - **break:** low bass and low density (today's `chill`);
  - **build:** brightness and density rising across the section while the bass thins, usually ending in a snare roll (density spike in its last 1-2 bars);
  - **drop:** high energy and bass straight after a build or a break;
  - **main:** groove without the drop's energy;
  - **outro:** the last section, energy falling.
- **Rank:** drops are ranked by how big the jump into them is. Only the top 1-2 drops of a song earn pyro.

**Accents:** beats whose kick or snare stands well above the local median (for example 1.8x the median over the surrounding 2 bars). These are the "important beats" a lighting designer hits even when they are not on a bar start: the last beat of a fill, a stab, the hit after a pause.

**Rolls:** stretches where 8th- or 16th-note onsets are dense, typically at the end of a build. Their rate drives the strobe speed.

**Output:**

```js
show = {
  sections: [{ from, to, kind: 'intro'|'main'|'build'|'drop'|'break'|'outro', rank }],
  energy: Float32Array (per bar), accents: Uint8Array (per beat, 0..3), rolls: [{ from, to, rate }],
}
```

A few kB per song; computed alongside the beat analysis, so no extra decode.

### 2. Director (runtime, per frame)

A small state machine that reads the show map at the current beat and drives all the fixtures through a few shared controls, like a lighting console's playbacks and effect engine.

**Layers, mixed every frame:**

1. **Master intensity** follows the bar energy, eased, so the whole rig breathes with the song.
2. **Look** (palette, fixture positions, laser pattern, beam pattern, screen mode) is chosen per section and varied every 4 bars within it. Changes land on phrase starts.
3. **Beat engine:** every beat gets an envelope that attacks instantly and decays exponentially, so lights flash in and out on every beat.
   - The decay speeds up with section energy: a long glow in a breakdown, a short punch in a drop.
   - Off-beats get a smaller hit in drops.
   - **Nothing holds still for more than one beat.** Fixtures move continuously: positions are a smooth function of the beat (sweeps, circles, figure-8s, fans opening and closing), not jumps followed by holds. In breaks the motion slows, but it never stops while music plays.
4. **Accents** trigger a bump on top of the beat engine: a flash of the LED edges and beams, a strobe hit, a laser snap to a new pattern. The bigger the accent, the more fixtures join.
5. **Section scripts**, the "chapters":
   - **intro / break:** low intensity, slow colour drifts, beams sweeping slowly, lasers off or one soft sheet, screens calm.
   - **build:** intensity ramps up over the section. Strobe rate follows the roll, from quarter notes to eighths to sixteenths. Beams tilt up and tighten. Lasers fan narrow and speed up. On the **last beat before the drop**, everything dips to near black for that beat (never fully black).
   - **drop:** the first downbeat is the big hit: everything at full, strobe and blinders on the first beat. Then the drop runs at high energy with movement changing every bar and laser patterns switching on accents. Pyro and laser shows are restricted (see below).
   - **main:** a medium version of the drop look, with no pyro.
   - **outro:** like break, fading with the energy.
6. **Pyro and laser budget** (the owner's rule):
   - In the top-ranked drops, from the first downbeat, a cue fires every 4 bars for at least 16 bars, as long as the beat holds every bar.
   - Pyro cues are flames, sparks and fireworks on the downbeat, plus an extra flame pop on strong accents.
   - Other drops get a full laser show in place of the pyro.
   - Each drop gets a different signature: drop 1 strobe and blinders plus pyro, drop 2 lasers plus fast sweeps, and so on.
   - Fireworks are timed so the burst lands on the downbeat (launched about 2 beats early).
7. **Fallback:** before a song's analysis is ready, or with the built-in beat, the director runs a generic loop (beat engine plus slow motion), like SoundSwitch's autoloops.

**Fixtures it drives** (existing objects; no new geometry needed):

- the LED wall and side screens (mode, palette, pulse);
- the LED edge strips;
- the beam cones;
- the truss strobes;
- the laser heads;
- the stage wash and crowd light;
- the moving-head rig (`rigG`);
- the flame machines, spark fountains and fireworks.

Each fixture group gets a few channels from the director: intensity, colour, position or pattern, and strobe. That's the same model as a DMX console's fixture groups.

### Performance budget

- **Analysis:** runs in the existing worker, once per song, adding a few ms to the current pass. It's cached on the song object with the beat analysis.
- **Director:** per frame it does a handful of lookups by beat index and evaluates fixture functions. There are no new draw calls; it changes uniforms, instance colours and matrices that are already updated each frame today.
- **Phones:** the same show, with fewer laser beams (for example 4 per head) and fewer firework particles if the frame rate drops below about 40 fps (measured over a few seconds).

### Testing

- **Test runs:** the instrumented headless test (`scratchpad/runtest.sh`, always muted) logs the show map for each song (sections, drops, accents). It captures frames at chosen beats: the last beat before a drop, the drop downbeat, mid-break.
- **"Never stuck" check:** sample fixture positions and intensities each beat. Fail if any visible fixture is unchanged for more than one beat while music plays.
- **By ear:** for 3-4 library songs, compare the detected drops and builds against listening, then tune the thresholds.

## Build order

1. Extend the analysis (features, sections, accents, rolls) and log it in the test for the library songs; tune until the drops and builds match what you hear.
2. The beat engine and continuous motion for beams, the rig and lasers. This fixes "stuck" on its own.
3. Section scripts (build, drop, break looks), the pre-drop dip, accents.
4. The pyro and laser budget on ranked drops; per-drop signatures.
5. Apply the same director to the club and rooftop rigs.

## Sources

- [Kinetic Festival Lighting Without Chaos: Movement Cues for Drops (Ticket Fairy)](https://www.ticketfairy.com/blog/kinetic-festival-lighting-without-chaos-movement-cues-for-drops)
- [Lighting for BPM Festivals: Timecode vs Busking (Ticket Fairy)](https://www.ticketfairy.com/blog/lighting-for-bpm-festivals-timecode-vs-busking.md)
- [Lighting the Festival Crowd for Safety and Euphoria (Ticket Fairy)](https://www.ticketfairy.com/blog/lighting-the-festival-crowd-for-safety-and-euphoria.md)
- [Using blinder lights to build hype (uking)](https://www.uking-online.com/blogs/stage-lighting-dmx-knowledge-hub/using-blinder-lights-to-build-hype)
- [How to use strobe lights like a pro DJ (Betopper)](https://jp.betopperdj.com/blogs/news/how-to-use-strobe-lights-like-a-pro-dj-for-bigger-stage-impact)
- [How to sync stage lights with music (SHEHDS)](https://shehds.com/blogs/news/how-to-sync-stage-lights-with-music-a-complete-guide)
- [ETC and EDM in harmony (LSI)](https://lsionline.co.uk/news/etc-and-edm-in-harmony--mzwmjn)
- [EDM song structure (Home DJ Studio)](https://homedjstudio.com/edm-song-structure/)
- [EDM arrangement (Inspired by Beatz)](https://www.inspiredbybeatz.com/en/edm-arrangement-from-loop-to-exciting-track/)
- [SoundSwitch autoscripting (inMusic support)](https://support.inmusicstore.com/en/support/solutions/articles/69000847098-autoscripting-audio-files-playlists-and-crates)
- [SoundSwitch software overview](https://www-soundswitch-com.netlify.app/software)
- [EDM structure features (arXiv 2603.08759)](https://arxiv.org/abs/2603.08759)
- [drop-detector (GitHub)](https://github.com/felixmeyer6/drop-detector)
- [FastLED drop and build-up detectors](https://fastled.io/docs/d0/d86/buildup_8cpp_8hpp_source.html)
- [Patent: lighting control from music structure, US 10390410](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10390410)
