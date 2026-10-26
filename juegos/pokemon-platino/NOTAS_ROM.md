Back Sprites:
poketool / trga / trbgra

Front Sprites:
poketool / trga / trfgra

HM Summon Sprites:
data / field_cutin

VS Faces:
graphic / field_encountereffect
IMPORTANT: For some reason the “mugshots” in platinum do not use the palettes in the field_encountereffect narc. Strangely, they actually pull from the palette in the front sprite narc above for that same character. So you need to take some extra steps to make the narc in field_encountereffect perfectly match the one in trfgra. You can do this by exporting the front sprite palette and importing it over the palette mugshot narc, or editing the mugshot narc with console tool. You can also see another work around demonstrated in this video:
Pokemon DS Rom Editing Tutorial Pt 2: Trainer Battle Sprites

Pokemon Sprites:
Regular Pokemon: poketool / pokegra / pl_pokegra
Pokemon with forms: poketool / pokegra / pl_otherpoke
	(You must use PokeDSpic for  the pl_otherpoke narc)

Pokemon Icons:
poketool / icongra / pl_poke_icon

Trainer Card:
graphic / trainer_case

Sprites:
trainer_case_31.RGCN

Palettes: 
From  trainer_case_0.RLCN to trainer_case_6.RLCN
trainer_case_26.RLCN

Map Icon:
graphic / tmap_gra

Sprites:
Hero & Heroine / Tmap_gra_10.RGCN
Hero & Heroine / Tmap_gra_11.RECN

Palette: 
Hero & Heroine / Tmap_gra_2.RLCN

Pokedex Size Comparison:
	resources / eng / zukan / zukan.narc 

Sprites:
File 93, the NCGR.
	File 91, the cells file. 
(You can try replacing the cells one by one instead 
of the whole RGCN at once.)

Palette: 
RLCN 14 (Palette #4)

Text File:
	msgdata / pl_msgdata

Arm9.bin:
	ftc / arm9.bin

Sound File:
	data / sound / pl_sound_data.sdat

Underground Entry Sprite:
data / ugeffect_obj_graphic

Sprites:
Hero / ugeffect_obj_graphic_0.RGCN
	Heroine / ugeffect_obj_graphic_2.RGCN
	Hole / ugeffect_obj_graphic_8.RGCN

Palettes: 
Hero / ugeffect_obj_graphic_1.RGCN
	Heroine / ugeffect_obj_graphic_3.RGCN

	(Hole shares the palettes with the player sprite, 
you’ll need to edit it the same way as the flying HM sprite.)

Legendary Pokemon Cutscene:
	arc / demo_tengan_gra

	Hero / demo_tengan_gra_61.BMD0
	Heroine / demo_tengan_gra_63.BMD0

Hall of Fame: (You will need to follow a tutorial to modify it.)
	poketool / trgra / trfgra.narc

	Sprites: 
Hero / trfgra_4.RGCN
Heroine / trfgra_9.RGCN

Palettes: 
Hero / trfgra_1.RLCN
Heroine / trfgra_6.RLCN

Name Entry Walking Sprite:
data / namein

	Sprites: 
	namein10.bin

Palette: 
namein_1.RLCN (Palette #4)

Title Screen:
demo / title / title_demo

Opening Video:
demo / title / op_demo

Intro Professor Talk:
	demo / intro / intro

Ending Credits:
	graphic / ending

Textbox Borders:
graphic / pl_winframe

Overworld Sprites:
	data / mmodel

	Hero:
		90 - Walking/Running
		92 - Bike
		155 - Pull out Pokeball
		157 - Water flower
		159 - Surf
164 - Tux
166 - Fishing
363 - Use Poketch
365 - Save
367 - Pokecenter
415 - VS Seeker

Heroine:
91 - Walking/Running
		93 - Bike
		156 - Pull out Pokeball
		158 - Water flower
		160 - Surf
165 - Dress
167 - Fishing
364 - Use Poketch
366 - Save
368 - Pokecenter
416 - VS Seeker
