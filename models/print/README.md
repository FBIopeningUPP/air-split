# Print files

Every part here is already turned the way it goes on the bed. Open it in the slicer and print with **no supports**.

| File | How many | Material |
|---|---|---|
| `fit_test_plate.stl` | 1, print it first | same as the case |
| `left_shell.stl`, `right_shell.stl` | 1 each | PLA or PETG |
| `left_base.stl`, `right_base.stl` | 1 each | PLA or PETG |
| `left_oled_bezel.stl`, `right_oled_bezel.stl` | 1 each | PLA or PETG |
| `left_cover.stl`, `right_cover.stl` | 1 each, optional | smoke or clear PETG |
| `left_tent_10.stl`, `right_tent_10.stl` (or 5, 15) | 1 each of the angle you want, optional | PLA or PETG, 15 to 20 % infill |

Settings: 0.2 mm layers (0.12 mm for smoother curves), 3 to 4 walls, 15 to 20 % infill, a smooth PEI or glass bed for a glossy top.

The same parts in their assembled position are in [`../stl`](../stl), and as STEP in [`../step`](../step). Details: [print section of the build guide](../../docs/BUILD.md#print).
