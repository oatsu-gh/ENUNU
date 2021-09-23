# ENUNU

This software allows you to use NNSVS-singing-models like as UTAU-VBs.

## Attention

This README_English.md file was transelated from README.md written in Japanese, using [MiraiTranslate](https://miraitranslate.com).

## Usage

1. Open UST and set the UTAU sound source containing the ENUNU model as VB.
   ex.) "おふとんP (ENUNU)" : NNSVS Ofuton-P singing voice model for ENUNU
2. Set Hiragana-CV lyric to each note.
3. Select the notes you want to play and launch ENUNU as a plug-in.
4. ~ Wait a few seconds or minutes ~
5. The selected WAV file is created in the same folder as the UST file.

## Tips

- It is recommended to include the consonant in the previous note.
  - \[さ]\[っ]\[ぽ]\[ろ] → \[さっ]\[ぽ]\[ろ]
- It does not support multi-syllable-hiragana-lyric in one note, except for "っ".
 Lets you enter phonemes directly, separated by spaces. Can be used with hiragana, but cannot be mixed in one note.
  - \[い]\[ら]\[ん]\[か]\[ら]\[ぷ]\[て] → \[i]\[r a]\[N]\[k a]\[ら]\[p]\[て]
- You can have more than one syllable in a note by entering phonemes directly.
  - \[さっ]\[ぽ]\[ろ] → \[さっ]\[p o r o]

## Terms of Use

Please follow the rules of each VB or singing-model when using. The terms of this software are provided separately as LICENSE files.




---

Following contents are for developers.

---



## Development Environment

- Windows 10
- Python 3.8
  - utaupy 1.14.1
  - numpy 1.21.2（do not use 1.19.4）
  - torch 1.7.0+cu101
  - nnsvs (develepment version)
  - nnmnkwii (develepment version)
- CUDA 11.0

## How to Create the UTAU Instrument Folder for ENUNU

You can use the normal NNSVS singing voice model, but it will be a little more stable if you use [Recipe exclusively for ENUNU](https://github.com/oatsu-gh/ENUNU/tree/main/nnsvs_recipe_for_enunu). It is recommended to include a redistributable UTAU solo sound source for musical interval checking during transcription.

### Using a normal model

Add enuconfig.yaml to the root directory of the model and rewrite it by referring to the P singing model of the futon for ENUNU. Use `question_path` to specify what you used for learning and include it. `trained\_for\_enunu` should be **`false` **.

### Using the model for ENUNU

Add enuconfig.yaml to the root directory of the model and rewrite it by referring to the P singing model of the futon for ENUNU. Use `question _ path` to specify what you used for learning and include it. `trained\_for\_enunu` should be **`true`**.



## Notes about LAB file format

The full context label specification is different from Sinsy's. Important differences include:.

- Does not handle information about phrases (e18 - e25, g, h, i, j3)
- Do not use musical symbols such as note strength (e 26 - e 56)
- does not deal with information about measures (e10 - e17, j2, j3)
- Does not handle beat information (c4, d4, e4)
- Relative note pitch (d2, e2, f2) specifications are different
  Since the key of the note cannot be obtained, the octave information is ignored and the relative pitch is assumed to be C = 0.
- Lock note key (d3, e3, f3) to 120
  - 120 if not manually specified
  Any value that is a multiple of -12 and does not appear on the Sinsy label can be substituted. (24, etc.)
- **Note and syllable information (a, c, d, f) are different with rest in between**
  - According to the Sinsy specification, the "Next Note" information in the note immediately before the rest points to the note after the rest, but this tool is designed to point to the rest.
  - Notes immediately following a rest are similarly designed to point to the rest itself, not to the start of the rest.
  - Same with syllables.
