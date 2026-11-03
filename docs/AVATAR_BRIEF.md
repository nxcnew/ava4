# New avatar: look and build brief

A brief for the first avatar built for Dance Arena from scratch. It is for whoever builds the character, whether that's the owner in Character Creator 4 or a commissioned artist. It also lists what the page must do with each part.

The face is an original design. The references set the style, not a likeness.

## References

These images in `walls/` set the look:

| Image | What to take from it |
|---|---|
| Neon Halo Concert Performance | High curly ponytail, fringe skirt, fishnets, silver boots |
| Silver Pop Concert Showdown | Silver fringe jacket, chain belts, layered necklaces, handheld mic |
| Neon Holographic Concert Performance | Hair flying mid-spin, holographic pleated skirt and jacket, stacked bracelets |
| Glamorous Singer Under Concert Lights (1) | Face: make-up, skin sheen, chandelier earrings, open-mouth singing |
| Moonlit Western Concert Spectacle | Boho fringe, turquoise jewellery, long hair |
| Glittering Purple Pop Concert | Beaded fringe, arm cuffs, garters, lace-up boots |
| Glamorous Blue-Violet Concert Performance | Jewelled bodysuit, sheer flowing cape, big curls |

## The character

### Skin

- **Tone:** warm olive to sun-kissed tan.
- **Finish:** a healthy sheen, with highlighter on the cheekbones, collarbones, shoulders and legs.
- **Detail:** visible pores and subtle freckling up close. The skin must not look plastic.

### Hair

- **Length:** long, to mid-back.
- **Shape:** voluminous loose curls and waves.
- **Colour:** dark brown, with a caramel balayage towards the ends.
- **Hairstyles:** two:
  - **loose:** for the head flips;
  - **high ponytail:** with the curls still loose.
- **Flyaways:** a few loose hairs at the hairline.

### Face

- **Look:** bold, confident and expressive.
- **Eyes:** full brows and long lashes.
- **Lips:** full lips.
- **Expressions:** every part of the face must be able to move, as listed under Rig requirements below.

### Make-up

| Look | Eyes | Lips | Face |
|---|---|---|---|
| Studio | soft smoky eye, thin liner | glossy nude | light glow |
| Stage | shimmer smoky eye with winged liner, lashes and glitter on the lids | glossy deep rose or red | contour, strong highlighter, glitter on cheekbones and shoulders |

### Outfit 1: Studio

- **Clothes:** a fitted crop top and loose joggers, with the waistband low on the hips.
- **Shoes:** trainers.
- **Jewellery:** small gold hoops, a thin necklace and a couple of bracelets.
- **Hair:** loose.

### Outfit 2: Stage

- **Top:** a metallic or sequined crop top, with optional straps and chain details.
- **Bottom:** a fringe skirt or belt made of beaded chains or metallic strands.
- **Legs:** fishnet tights.
- **Boots:** knee-high silver heeled boots.
- **Jewellery:** big hoop or chandelier earrings, two or three layered chains, stacked bracelets and arm cuffs.
- **Optional:** a short fringe jacket or a sheer cape worn off the shoulders.
- **Prop:** a handheld microphone, as a separate object.

## Rig requirements

These are additions to the spec in [CHARACTER_PIPELINE.md](CHARACTER_PIPELINE.md) section 6.

### Skeleton

- **Bones:** Mixamo-compatible, with **all fingers**: three joints per finger, plus the thumb.
- **Face bones:** jaw, both eyes and the tongue.

### Face shapes

- **Full ARKit 52.**
- **CC extended set** where available, especially the tongue shapes (out, up, down, left, right, tip up) and separate left and right versions of every eye, brow, cheek and mouth-corner shape.
- **Placement:** all shapes on a separate, triangulated head mesh, as in section 6. Teeth and tongue are separate meshes that follow the jaw.

### Outfits

- **Shared skeleton:** both outfits use the same skeleton and body, so dances and physics work the same in both.
- **Files:** one file per outfit, or one file with each outfit's meshes named clearly.

### Physics bones

Every part that should move on its own gets a spring chain, named per section 3 of the pipeline doc.

| Part | Chains | Bones per chain | Physics feel |
|---|---|---|---|
| Loose hair | 30-60 curl clumps | 6-10 | light, with gravity, swings out in spins |
| Ponytail | 1 main plus 4-6 clumps | 8-10 | swings and whips on head turns |
| Hoop and chandelier earrings | 1 per earring | 2 | heavy pendulum, little damping |
| Layered necklaces | 2-3 | 4-6 | slides over the chest, collides with the body |
| Bracelets and cuffs | none | — | follow the wrist and forearm |
| Joggers | 2-4 around each leg, loose | 2-3 | soft, heavy, damped |
| Fringe skirt and belt | 12-24 groups | 3-4 | fans out on hip moves; see the note below |
| Fringe jacket and cape | 8-16 | 4-6 | trails behind the arms and turns |
| Body | small soft-tissue bones (chest, glutes, thighs) | 1 | subtle, tightly damped |

**Note on fringe:** each group of strands moves as one bone chain. Individual strands inside a group get extra sway from a vertex shader on the page, so hundreds of strands don't need hundreds of bones.

### Prop

- **Microphone:** exported as its own mesh, with a socket point in the right hand. The page attaches it and poses the fingers around it.

## Page features this avatar needs

None of these exist yet. Each one is planned work in `index.html`.

### Expressions and hands

- **Expression performer:**
  - expressions: smile, laugh, wink, tongue tease, pout or kiss, "woo" open mouth, singing;
  - looking into the camera.
- **Lip sync:** singing roughly in time with the vocals.
- **Hand-pose layer:** finger poses blended over the dances, including the grip on the microphone.

### Physics

- **Spring kinds:** new kinds for curls, ponytails, jewellery and fringe.
- **More colliders:** neck, shoulders, arms and hands.
- **Fixed physics step:** the physics runs at a steady rate, independent of frame rate.

### Materials

- **Skin:** a subsurface approximation, so light glows slightly through it.
- **Hair:** a shader with highlights that run along the strands.
- **Eyes:** wet-looking eyes.
- **Glitter and sequins:** sparkles that flicker as the dancer and lights move.
- **Costume surfaces:** holographic film, chrome boots and metal jewellery.

### Outfits

- **Switching:** the studio outfit in the Studio, and the stage outfit on the festival main stage.

## Budget

These are targets for a real-time web page. This avatar is the main dancer, so it gets more than the others.

- **Triangles:** about 80-120k for the body and outfit, plus the hair cards.
- **Textures:**
  - **face:** 4K, or 2K plus a detail normal map;
  - **body and outfit:** 2K.
- **File size:** under about 40 MB per outfit after `shrink-fbx.py`. GLB with compressed textures would be smaller.

**Limit on realism:** the page can get close to these references, but not to the photographs themselves. Path-traced lighting and true strand-level hair are not possible in real time in a browser.
