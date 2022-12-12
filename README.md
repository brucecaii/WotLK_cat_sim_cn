# Nerd Ecat Sims

本模拟器为Wowhead野德版主Nerdegghead以及美服Discord TC频道共同开发

中文版本由范克瑞斯Espeon进行翻译,优化,更新,以及代码编译

任何问题请到B站站内信咨询 https://space.bilibili.com/919498

Github https://github.com/eeveecc/WotLK_cat_sim_cn

## Release Note

```
2022.10.29 修复了冰爪急速默认开启的BUG
2022.11.3  修正翻译,增加平砍重置
2022.11.10 增加回蓝BUFF,支持爪子舞(包括平砍延迟)/神像舞,优化平砍,增加T8效果
2022.12.12 优化代码,根据奥杜尔PTR修正装备数据
```

## Compile

`pyinstaller -F main.py player.py sim_utils.py trinkets.py wotlk_cat_sim.py`