# -*- coding: utf-8 -*-

# Run this app with `python main.py` and
# visit http://127.0.0.1:8080/ in your web browser.

import dash
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objects as go
import numpy as np
from dash.dependencies import Input, Output, State
import dash_bootstrap_components as dbc
import wotlk_cat_sim as ccs
import sim_utils
import player as player_class
import multiprocessing
import trinkets
import copy
import json
import base64
import io


app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])
server = app.server

default_input_stats = {
        "agility": 1456,
        "armor": 6675,
        "armorPen": 43,
        "armorPenRating": 602,
        "attackPower": 8543,
        "crit": 53.34,
        "critRating": 615,
        "critReduction": 6,
        "defense": 400,
        "dodge": 40,
        "expertise": 25,
        "expertiseRating": 126,
        "feralAttackPower": 3001,
        "haste": 10.94,
        "hasteRating": 276,
        "health": 21517,
        "hit": 6.89,
        "hitRating": 226,
        "intellect": 206,
        "mainHandSpeed": 2.4,
        "mana": 6306,
        "natureResist": 10,
        "parry": 5,
        "spellCrit": 16.48,
        "spellCritRating": 615,
        "spellHaste": 8.42,
        "spellHit": 8.62,
        "spirit": 189,
        "stamina": 1428,
        "strength": 251
}

stat_input = dbc.Col([
    html.H5('使用指南'),
    dcc.Markdown(
        '欢迎使用WLK猫德模拟器!',
        style={'width': 300},
    ),
    dcc.Markdown(
        '模拟器源代码 https://github.com/eeveecc/WotLK_cat_sim_cn',
        style={'width': 300},
    ),
    dcc.Markdown(
        '更多信息参考 https://space.bilibili.com/919498',
        style={'width': 300},
    ),
    dcc.Markdown(
        '本模拟器需要用到Eighty Upgrades的配装导出文件.'
        '在你的配装页面的右上角,选择Export,并且选择Cat Form,然后导出.'
        '确保你勾选了Talent(天赋),取消勾选Buff(因为你可以在模拟器里选择).'
        '同时确保你把饰品和神像都留空,在模拟器界面里设置即可',
        style={'width': 300},
    ),
    dcc.Markdown(
        'Eighty Upgrades https://eightyupgrades.com/',
        style={'width': 300},
    ),
    dcc.Upload(
        id='upload-data',
        children=html.Div([
            '把装备配置文件拉到这里或者',
            html.A('选择文件')
        ]),
        style={
            'width': '100%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'margin': '0px'
        },
        # Don't allow multiple files to be uploaded
        multiple=False
    ),
    html.Br(),
    html.Div(
        '没有选择文件,正在使用默认属性参数',
        id='upload_status', style={'color': '#E59F3A'}
    ),
    html.Br()
], width='auto', style={'marginBottom': '20px', 'marginLeft': '10px'})

buffs_1 = dbc.Col(
    [dbc.Collapse([html.H5('合剂和食物'),
     dbc.Checklist(
         options=[{'label': '无尽怒气合剂(180AP)', 'value': 'flask'},
                  {'label': '钳鱼大餐/生拌狼肉糜(40命中)', 'value': 'hit_food'},
                  {'label': '熏烤龙鳞鱼(40敏捷)', 'value': 'agi_food'},
                  {'label': '龙鳞鱼片(40力量)', 'value': 'str_food'},
                  {'label': '犀牛大餐(40破甲)', 'value': 'arp_food'}],
         value=['flask', 'agi_food'],
         id='consumables'
    ),
        html.Br(),
        html.H5('团队Buff'),
        dbc.Checklist(
         options=[
             {
                 'label': '王者祝福',
                 'value': 'kings'
             },
             {
                 'label': '力量祝福/战斗怒吼',
                 'value': 'might'
             },
             {
                 'label': '智慧祝福',
                 'value': 'wisdom'
             },
             {
                 'label': '野性赐福',
                 'value': 'motw'
             },
             {
                 'label': '英勇灵气',
                 'value': 'heroic_presence'
             },
             {
                 'label': '大地之力图腾/寒冬号角',
                 'value': 'str_totem'
             },
             {
                 'label': "怒火释放/强击光环/憎恶之力",
                 'value': 'unleashed_rage'
             },
             {
                 'label': '奥术智慧',
                 'value': 'ai'
             },
             {
                 'label': '精神祷言',
                 'value': 'spirit'
             }
         ],
         value=[
             'kings', 'might', 'wisdom', 'motw', 'str_totem', 'unleashed_rage',
             'ai', 'spirit'
         ],
         id='raid_buffs'
    ),
        html.Br()], id='buff_section', is_open=True),
        html.H5('光环'),
        dbc.Checklist(
        options=[
            {
                'label': '圣洁惩戒/凶猛灵感/奥术增效',
                'value': 'sanc_aura'
            },
            {
                'label': '强化风怒图腾/强化冰爪',
                'value': 'major_haste'
            },
            {
                'label': '强化枭兽形态/迅捷惩戒',
                'value': 'minor_haste'
            },
            {
                'label': '空气之怒图腾',
                'value': 'spell_haste'
            },
            {
                'label': '智慧审判',
                'value': 'replenishment'
            },
        ],
        value=[
            'sanc_aura', 'major_haste', 'minor_haste', 'spell_haste',
            'replenishment'
        ],
        id='other_buffs'
    ),
        dbc.InputGroup(
        [
            dbc.InputGroupAddon(
                '回春术/野性成长 奶德治疗覆盖:', addon_type='prepend'
            ),
            dbc.Input(
                value=0.0, type='number', id='hot_uptime',
            ),
            dbc.InputGroupAddon('%', addon_type='append')
        ],
        style={'width': '75%', 'marginTop': '2.5%'}
    ),
        html.Br(),
        html.H5('神像,雕文,以及其他特殊增益'),
        html.H5('(选择腐蚀者和凶兽会打完第一个裂伤后更换神像)'),
        dbc.Checklist(
        options=[{'label': '乌鸦神像', 'value': 'raven'}],
        value=[], id='raven_idol'
    ),
        dbc.Checklist(
        options=[
            {'label': '凶兽神像', 'value': 'shred_idol'},
            {'label': '膜拜神像', 'value': 'rip_idol'},
            {'label': '残毁神像', 'value': 'idol_of_mutilation'},
            {'label': '泣月神像', 'value': 'rake_idol'},
            {'label': '腐蚀者神像', 'value': 'mangle_idol'},
            {'label': '裂伤雕文', 'value': 'mangle_glyph'},
            {'label': '割裂雕文', 'value': 'rip_glyph'},
            {'label': '撕碎雕文', 'value': 'shred_glyph'},
            {'label': '咆哮雕文', 'value': 'roar_glyph'},
            {'label': '狂暴雕文', 'value': 'berserk_glyph'},
            {'label': '2T6', 'value': 't6_2p'},
            {'label': '4T6', 'value': 't6_4p'},
            {'label': '2T7', 'value': 't7_2p'},
            {'label': '2T8', 'value': 't8_2p'},
            {'label': '4T8', 'value': 't8_4p'},
            {'label': '2T9', 'value': 't9_2p'},
            {'label': '4T9', 'value': 't9_4p'},
            {'label': '2T10', 'value': 't10_2p'},
            {'label': '4T10', 'value': 't10_4p'},
            {'label': '狼头之盔', 'value': 'wolfshead'},
            {'label': '残酷多彩', 'value': 'meta'},
            {'label': '武器猫鼬', 'value': 'mongoose'},
            {'label': '武器狂暴', 'value': 'berserking'},
            {'label': '手套加速器', 'value': 'engi_gloves'},
        ],
        value=[
            'shred_idol', 'mangle_idol', 'rip_glyph', 'shred_glyph',
            'roar_glyph', 't8_2p', 'meta', 'berserking', 'engi_gloves'
        ],
        id='bonuses'
    ),
    ],
    width='25%', style={'marginBottom': '20px', 'marginLeft': '30px'}
)

encounter_details = dbc.Col(
    [html.H4('战斗设置'),
     dbc.InputGroup(
         [
             dbc.InputGroupAddon('时长', addon_type='prepend'),
             dbc.Input(
                 value=180.0, type='number', id='fight_length',
             ),
             dbc.InputGroupAddon('秒', addon_type='append')
         ],
         style={'width': '75%'}
    ),
        dbc.InputGroup(
         [
             dbc.InputGroupAddon('敌人护甲', addon_type='prepend'),
             dbc.Input(value=10643, type='number', id='boss_armor')
         ],
         style={'width': '75%'}
    ),
        dbc.InputGroup(
         [
            dbc.InputGroupAddon('AOE战目标数量', addon_type='prepend'),
            dbc.Input(value=1, type='number', id='num_targets')
         ],
        style={'width': '75%'}
    ),
        html.Br(),
        html.H5('伤害增益Debuff'),
        dbc.Checklist(
         options=[
             {
                 'label': '阿尔萨斯礼物',
                 'value': 'gift_of_arthas'
             },
             {
                 'label': '破甲',
                 'value': 'sunder'
             },
             {
                 'label': '精灵火',
                 'value': 'faerie_fire'
             },
             {
                 'label': '血性狂乱/野蛮战斗',
                 'value': 'blood_frenzy'
             },
             {
                'label': "元素诅咒 / 大地与月亮 / 黑色热疫使者",
                'value': 'curse_of_elements'
             },
         ],
         value=['gift_of_arthas', 'sunder', 'faerie_fire', 'blood_frenzy', 'curse_of_elements'],
         id='boss_debuffs'
    ),
        dbc.Checklist(
         options=[
             {
                 'label': '十字军之心/毒物大师',
                 'value': 'jotc'
             },
             {'label': '智慧审判', 'value': 'jow'},
             {'label': '悲惨 / 强化精灵火', 'value': 'misery'},
             {
                 'label': '暗影掌握 / 强化灼烧 / 深冬之寒',
                 'value': 'shadow_mastery'
             },
         ],
         value=['jotc', 'jow', 'misery', 'shadow_mastery'],
         id='stat_debuffs',
    ),
        html.Br(),
        html.H5('即时技能冷却'),
        dbc.Checklist(
         options=[
             {'label': '嗜血/英勇', 'value': 'lust'},
             {'label': '狂乱', 'value': 'unholy_frenzy'},
             {'label': '碎裂投掷', 'value': 'shattering_throw'},
         ],
         value=['lust', 'shattering_throw'], id='cooldowns',
    ),
        dbc.InputGroup(
         [
             dbc.InputGroupAddon('药水', addon_type='prepend'),
             dbc.Select(
                 options=[
                     {'label': '加速药水', 'value': 'haste'},
                     {'label': '空', 'value': 'none'},
                 ],
                 value='haste', id='potion',
             ),
         ],
         style={'width': '75%', 'marginTop': '1.5%'}
    ),
        html.Br(),
        html.H5('天赋'),
        dbc.Checklist(
         options=[
             {'label': '清晰预兆', 'value': 'omen'},
             {'label': '狂暴', 'value': 'berserk'},
             {'label': '原始血瘀', 'value': 'primal_gore'},
         ],
         value=['omen', 'berserk', 'primal_gore'], id='binary_talents'
    ),
        html.Br(),
        html.Div([
            html.Div(
                '野性侵略',
                style={
                 'width': '35%', 'display': 'inline-block',
                 'fontWeight': 'bold'
             }
         ),
         dbc.Select(
             options=[
                 {'label': '0', 'value': 0},
                 {'label': '1', 'value': 1},
                 {'label': '2', 'value': 2},
                 {'label': '3', 'value': 3},
                 {'label': '4', 'value': 4},
                 {'label': '5', 'value': 5},
             ],
             value=5, id='feral_aggression',
             style={
                 'width': '20%', 'display': 'inline-block',
                 'marginBottom': '2.5%', 'marginRight': '5%'
             }
         )]),
     html.Div([
         html.Div(
             '野蛮暴怒:',
             style={
                 'width': '35%', 'display': 'inline-block',
                 'fontWeight': 'bold'
                 }
            ),
            dbc.Select(
                options=[
                    {'label': '0', 'value': 0},
                    {'label': '1', 'value': 1},
                    {'label': '2', 'value': 2},
                ],
                value=2, id='savage_fury',
                style={
                    'width': '20%', 'display': 'inline-block',
                    'marginBottom': '2.5%', 'marginRight': '5%'
                }
            )]),
        html.Div([
            html.Div(
                '强化兽群卫士',
                style={
                 'width': '35%', 'display': 'inline-block',
                 'fontWeight': 'bold'
             }
         ),
         dbc.Select(
             options=[
                 {'label': '0', 'value': 0},
                 {'label': '1', 'value': 1},
                 {'label': '2', 'value': 2},
                 {'label': '3', 'value': 3},
             ],
             value='0', id='potp',
             style={
                 'width': '20%', 'display': 'inline-block',
                 'marginBottom': '2.5%', 'marginRight': '5%'
             }
         )]),
     html.Div([
         html.Div(
             '狩猎天性:',
             style={
                 'width': '35%', 'display': 'inline-block',
                 'fontWeight': 'bold'
                 }
            ),
            dbc.Select(
                options=[
                    {'label': '0', 'value': 0},
                    {'label': '1', 'value': 1},
                    {'label': '2', 'value': 2},
                    {'label': '3', 'value': 3},
                ],
                value=3, id='predatory_instincts',
                style={
                    'width': '20%', 'display': 'inline-block',
                    'marginBottom': '2.5%', 'marginRight': '5%'
                }
            )]),
        html.Div([
            html.Div(
                '强化裂伤',
                style={
                 'width': '35%', 'display': 'inline-block',
                 'fontWeight': 'bold'
                 }
            ),
            dbc.Select(
                options=[
                    {'label': '0', 'value': 0},
                    {'label': '1', 'value': 1},
                    {'label': '2', 'value': 2},
                    {'label': '3', 'value': 3},
                ],
                value='0', id='improved_mangle',
                style={
                    'width': '20%', 'display': 'inline-block',
                    'marginBottom': '2.5%', 'marginRight': '5%'
                }
            )]),
        html.Div([
            html.Div(
                '强化野性赐福',
                style={
                 'width': '35%', 'display': 'inline-block',
                 'fontWeight': 'bold'
                 }
            ),
            dbc.Select(
                options=[
                    {'label': '0', 'value': 0},
                    {'label': '1', 'value': 1},
                    {'label': '2', 'value': 2},
                ],
                value=2, id='imp_motw',
                style={
                    'width': '20%', 'display': 'inline-block',
                    'marginBottom': '2.5%', 'marginRight': '5%'
                }
            )]),
        html.Div([
            html.Div(
                '激怒',
                style={
                 'width': '35%', 'display': 'inline-block',
                 'fontWeight': 'bold'
             }
         ),
         dbc.Select(
             options=[
                 {'label': '0', 'value': 0},
                 {'label': '1', 'value': 1},
                 {'label': '2', 'value': 2},
                 {'label': '3', 'value': 3},
                 {'label': '4', 'value': 4},
                 {'label': '5', 'value': 5},
             ],
             value=3, id='furor',
             style={
                 'width': '20%', 'display': 'inline-block',
                 'marginBottom': '2.5%', 'marginRight': '5%'
             }
         )]),
     html.Div([
         html.Div(
             '自然主义:',
             style={
                 'width': '35%', 'display': 'inline-block',
                 'fontWeight': 'bold'
                 }
            ),
            dbc.Select(
                options=[
                    {'label': '0', 'value': 0},
                    {'label': '1', 'value': 1},
                    {'label': '2', 'value': 2},
                    {'label': '3', 'value': 3},
                    {'label': '4', 'value': 4},
                    {'label': '5', 'value': 5},
                ],
                value=5, id='naturalist',
                style={
                    'width': '20%', 'display': 'inline-block',
                    'marginBottom': '2.5%', 'marginRight': '5%'
                }
            )]),
        html.Div([
            html.Div(
                '自然变形',
                style={
                 'width': '35%', 'display': 'inline-block',
                 'fontWeight': 'bold'
                 }
            ),
            dbc.Select(
                options=[
                    {'label': '0', 'value': 0},
                    {'label': '1', 'value': 1},
                    {'label': '2', 'value': 2},
                    {'label': '3', 'value': 3},
                ],
                value=3, id='natural_shapeshifter',
                style={
                    'width': '20%', 'display': 'inline-block',
                    'marginBottom': '2.5%', 'marginRight': '5%'
                }
            )]),
        html.Div([
            html.Div(
                '强化兽群领袖',
                style={
                 'width': '35%', 'display': 'inline-block',
                 'fontWeight': 'bold'
                 }
            ),
            dbc.Select(
                options=[
                    {'label': '0', 'value': 0},
                    {'label': '1', 'value': 1},
                    {'label': '2', 'value': 2},
                ],
                value=1, id='ilotp',
                style={
                    'width': '20%', 'display': 'inline-block',
                    'marginBottom': '2.5%', 'marginRight': '5%'
                }
            )])],
    width='auto',
    style={
        'marginLeft': '10px', 'marginBottom': '20px'
    }
)

# Sim replicates input
iteration_input = dbc.Col([
    html.H4('模拟器配置'),
    dbc.InputGroup(
        [
            dbc.InputGroupAddon('样本数量', addon_type='prepend'),
            dbc.Input(value=30000, type='number', id='num_replicates')
        ],
        style={'width': '100%'}
    ),
    dbc.InputGroup(
        [
            dbc.InputGroupAddon('模拟游戏延迟', addon_type='prepend'),
            dbc.Input(
                value=100, type='number', id='latency', min=1, step=1,
            ),
            dbc.InputGroupAddon('ms', addon_type='append')
        ],
        style={'width': '100%'}
    ),
    html.Br(),
    html.H5('输出循环策略'),
    dbc.InputGroup(
        [
            dbc.InputGroupAddon(
                '割裂星', addon_type='prepend'
            ),
            dbc.Select(
                options=[
                    {'label': '3', 'value': 3},
                    {'label': '4', 'value': 4},
                    {'label': '5', 'value': 5},
                ],
                value=5, id='rip_cp',
            ),
        ],
        style={'width': '100%', 'marginBottom': '1.5%'}
    ),
    dbc.InputGroup(
        [
            dbc.InputGroupAddon(
                '凶猛星',
                addon_type='prepend'
            ),
            dbc.Select(
                options=[
                    {'label': '3', 'value': 3},
                    {'label': '4', 'value': 4},
                    {'label': '5', 'value': 5},
                ],
                value=5, id='bite_cp',
            ),
        ],
        style={'width': '100%', 'marginBottom': '1.5%'}
    ),
    dbc.InputGroup(
        [
            dbc.InputGroupAddon('等待', addon_type='prepend'),
            dbc.Input(
                value=0.0, min=0.0, step=0.5, type='number', id='cd_delay',
            ),
            dbc.InputGroupAddon(
                '秒后使用技能', addon_type='append'
            ),
        ],
        style={'width': '100%', 'marginBottom': '1.5%'},
    ),
    dbc.InputGroup(
        [
            dbc.InputGroupAddon(
                '保持咆哮和割间隔', addon_type='prepend'
            ),
            dbc.Input(
                value=24, min=0, step=1, type='number', id='min_roar_offset'
            ),
            dbc.InputGroupAddon('秒(4T8为34秒,其他24秒)', addon_type='append')
        ],
        style={'width': '100%', 'marginBottom': '1.5%'}
    ),
    dbc.InputGroup(
        [
            dbc.InputGroupAddon(
                '割裂余地(Leeway)延迟设置:', addon_type='prepend'
            ),
            dbc.Input(
                value=3, min=0, step=1, type='number', id='roar_clip_leeway'
            ),
            dbc.InputGroupAddon('seconds', addon_type='append')
        ],
        style={'width': '100%', 'marginBottom': '1.5%'}
    ),
    dbc.InputGroup(
        [
            dbc.InputGroupAddon(
                '精灵火能量上限:',
                addon_type='prepend'
            ),
            dbc.Input(
                value=15, min=0, step=1, type='number', id='berserk_ff_thresh'
            ),
        ],
        style={'width': '100%', 'marginBottom': '1.5%'}
    ),
    dbc.InputGroup(
        [
            dbc.InputGroupAddon(
                '最高精灵火延迟:',
                addon_type='prepend'
            ),
            dbc.Input(
                value=0.7, min=0, step=0.1, type='number', id='max_ff_delay'
            ),
            dbc.InputGroupAddon('seconds', addon_type='append')
        ],
        style={'width': '100%'}
    ),
    html.Br(),
    dbc.Checklist(
        options=[{'label': '允许打凶猛', 'value': 'bite'}],
        value=['bite'], id='use_biteweave'
    ),
    dbc.Collapse(
        [
            dbc.InputGroup(
                [
                    dbc.InputGroupAddon(
                        '狂暴时打凶猛的最高能量',
                        addon_type='prepend'
                    ),
                    dbc.Input(
                        value=25, min=18, step=1, type='number',
                        id='berserk_bite_thresh'
                    )
                ],
                style={
                    'width': '90%', 'marginBottom': '1%', 'marginLeft': '5%'
                }
            ),
            dbc.InputGroup(
                [
                    dbc.InputGroupAddon(
                        '凶猛判定模型', addon_type='prepend'
                    ),
                    dbc.Select(
                        options=[
                            {'label': '智能分析判定', 'value': 'analytical'},
                            {'label': '经验判定(最优)', 'value': 'empirical'}
                        ],
                        value='empirical', id='bite_model'
                    ),
                ],
                style={
                    'width': '90%', 'marginBottom': '1%', 'marginLeft': '5%'
                }
            ),
            dbc.Collapse(
                [
                    dbc.InputGroup(
                        [
                            dbc.InputGroupAddon(
                                '当野蛮咆哮和割裂还剩余',
                                addon_type='prepend'
                            ),
                            dbc.Input(
                                type='number', value=4, id='bite_time',
                                min=0, step=1
                            )
                        ],
                        style={
                            'width': '90%', 'marginBottom': '1%',
                            'marginLeft': '5%'
                        }
                    ),
                ],
                id='empirical_options', is_open=True
            ),
        ],
        id='biteweave_options', is_open=True
    ),
    dbc.Checklist(
        options=[{'label': '允许打斜掠', 'value': 'use_rake'}],
        value=['use_rake'], id='use_rake'
    ),
    dbc.Checklist(
        options=[{'label': '优先打裂伤(正面攻击)', 'value': 'mangle_spam'}],
        value=[], id='mangle_spam'
    ),
    dbc.Checklist(
        options=[{
            'label': '熊T和武器战负责流血Debuff',
            'value': 'bear_mangle'
        }], value=[], id='bear_mangle'
    ),
    dbc.Collapse(
        [
            dbc.Checklist(
                options=[{
                    'label': '战斗前提前开狂暴',
                    'value': 'prepop_berserk'
                }], value=[], id='prepop_berserk'
            ),
        ],
        id='berserk_options', is_open=True
    ),
    dbc.Collapse(
        [
            dbc.Checklist(
                options=[{
                    'label': '战斗前偷清晰',
                    'value': 'preproc_omen'
                }], value=['preproc_omen'], id='preproc_omen'
            ),
        ],
        id='omen_options', is_open=True
    ),
    dbc.Checklist(
        options=[{'label': '熊猫舞流派', 'value': 'bearweave'}],
        value=[], id='bearweave'
    ),
    dbc.Collapse(
        [
            dbc.Checklist(
                options=[{
                    'label': '割伤舞(取消勾选时为裂伤舞)',
                    'value': 'lacerate_prio'
                }],
                value=[], id='lacerate_prio',
                style={'marginTop': '1%', 'marginLeft': '5%'}
            ),
            dbc.Collapse(
                [
                    dbc.InputGroup(
                        [
                            dbc.InputGroupAddon(
                                '割伤时间小于',
                                addon_type='prepend'
                            ),
                            dbc.Input(
                                type='number', value=8, id='lacerate_time',
                                min=0, step=1
                            ),
                            dbc.InputGroupAddon(
                                '秒时允许刷新', addon_type='append'
                            )
                        ],
                        style={
                            'width': '90%', 'marginBottom': '1%',
                            'marginLeft': '5%', 'marginTop': '1%',
                        }
                    ),
                ],
                id='lacerate_options', is_open=True
            ),
            dbc.Checklist(
                options=[{
                    'label': '允许二次变熊回怒',
                    'value': 'powerbear'
                }],
                value=[], id='powerbear',
                style={'marginTop': '1%', 'marginLeft': '5%'}
            ),
            dbc.Checklist(
                options=[{
                    'label': '平砍重置(换神像/武器/白蛇)',
                    'value': 'snek'
                }],
                value=['snek'], id='snek',
                style={'marginTop': '1%', 'marginLeft': '5%'}
            ),
        ],
        id='bearweave_options', is_open=True
    ),
    dbc.Checklist(
        options=[{'label': '爪子舞流派', 'value': 'flowershift'}],
        value=[], id='flowershift'
    ),
    dbc.Collapse(
        [
            dbc.InputGroup(
                [
                    dbc.InputGroupAddon(
                        '团队内友方目标数量(包括宠物):',
                        addon_type='prepend'
                    ),
                    dbc.Input(
                        type='number', value=30, id='gotw_targets', min=1,
                        step=1
                    )
                ],
                style={
                    'width': '90%', 'marginBottom': '1%', 'marginLeft': '5%',
                    'marginTop': '1%',
                }
            ),
            dbc.Checklist(
                options=[{
                    'label': '快速武器延迟平砍',
                    'value': 'daggerweave'
                }],
                value=[], id='daggerweave',
                style={'marginTop': '1%', 'marginLeft': '5%'}
            ),
            dbc.Collapse(
                [
                    dbc.InputGroup(
                        [
                            dbc.InputGroupAddon(
                                '更换武器EP损失(默认碎裂重锤BIS)',
                                addon_type='prepend'
                            ),
                            dbc.Input(
                                type='number', value=1415, id='dagger_ep_loss',
                                min=0, step=1
                            ),
                        ],
                        style={
                            'width': '90%', 'marginBottom': '1%',
                            'marginLeft': '5%', 'marginTop': '1%',
                        }
                    ),
                ],
                id='dagger_options', is_open=True
            ),
        ],
        id='flowershift_options', is_open=True
    ),
    html.Br(),
    html.H5('饰品'),
    dbc.Row([
        dbc.Col(dbc.Select(
            id='trinket_1',
            options=[
                {'label': '----空----', 'value': 'none'},
                {'label': "死神的意志(H)", 'value': 'dbw'},
                {'label': '密语尖牙颅骨(H)','value': 'whispering_fanged_skull'},
                {'label': '死亡的裁决(H)', 'value': 'deaths_verdict_heroic'},
                {'label': '死亡的裁决(N)','value': 'deaths_verdict_normal'},
                {'label': '彗星之痕', 'value': 'comet_trail'},
                {'label': '雷神符石', 'value': 'mjolnir_runestone'},
                {'label': '黑暗物质', 'value': 'dark_matter'},
                {'label': '蓝铁灌注器', 'value': 'pyrite_infuser'},
                {'label': '天谴之石', 'value': 'wrathstone'},
                {'label': '古神之血', 'value': 'blood_of_the_old_god'},
                {'label': '伟大卡牌(力量)','value': 'dmcg_str',},
                {'label': '伟大卡牌(敏捷)','value': 'dmcg_agi',},
                {'label': '死亡之钟', 'value': 'grim_toll'},
                {'label': '真实之镜', 'value': 'mirror'},
                {'label': "洛欧塞布之影", 'value': 'loatheb'},
                {'label': '陨星磨石', 'value': 'whetstone'},
                {'label': '五色巨龙之怒','value': 'fury_of_the_five_flights',},
                {'label': '门牙碎片', 'value': 'incisor_fragment'},
                {'label': '诺甘农的印记', 'value': 'norgannon'},
                {'label': "红龙血珠", 'value': 'sphere'},
                {'label': '通灵能量精粹', 'value': 'extract'},
                {'label': "盗匪的徽记", 'value': 'bandits_insignia'},
                {'label': '死亡卡牌', 'value': 'dmcd'},
                {'label': '悲苦之泪', 'value': 'tears'}
            ],
            value='mjolnir_runestone'
        )),
        dbc.Col(dbc.Select(
            id='trinket_2',
            options=[
                {'label': '----空----', 'value': 'none'},
                {'label': "死神的意志(H)", 'value': 'dbw'},
                {'label': '密语尖牙颅骨(H)','value': 'whispering_fanged_skull'},
                {'label': '死亡的裁决(H)', 'value': 'deaths_verdict_heroic'},
                {'label': '死亡的裁决(N)','value': 'deaths_verdict_normal'},
                {'label': '彗星之痕', 'value': 'comet_trail'},
                {'label': '雷神符石', 'value': 'mjolnir_runestone'},
                {'label': '黑暗物质', 'value': 'dark_matter'},
                {'label': '蓝铁灌注器', 'value': 'pyrite_infuser'},
                {'label': '天谴之石', 'value': 'wrathstone'},
                {'label': '古神之血', 'value': 'blood_of_the_old_god'},
                {'label': '伟大卡牌(力量)','value': 'dmcg_str',},
                {'label': '伟大卡牌(敏捷)','value': 'dmcg_agi',},
                {'label': '死亡之钟', 'value': 'grim_toll'},
                {'label': '真实之镜', 'value': 'mirror'},
                {'label': "洛欧塞布之影", 'value': 'loatheb'},
                {'label': '陨星磨石', 'value': 'whetstone'},
                {'label': '五色巨龙之怒','value': 'fury_of_the_five_flights',},
                {'label': '门牙碎片', 'value': 'incisor_fragment'},
                {'label': '诺甘农的印记', 'value': 'norgannon'},
                {'label': "红龙血珠", 'value': 'sphere'},
                {'label': '通灵能量精粹', 'value': 'extract'},
                {'label': "盗匪的徽记", 'value': 'bandits_insignia'},
                {'label': '死亡卡牌', 'value': 'dmcd'},
                {'label': '悲苦之泪', 'value': 'tears'}
            ],
            value='dark_matter'
        )),
    ]),
    html.Div([
        dbc.Row([
            dbc.Col(
                dcc.Markdown('战前饰品CD(默认0)'),
                id="trinket_icd_text_1"
            ),
            dbc.Col(
                dcc.Markdown('战前饰品CD(默认0)'),
                id="trinket_icd_text_2"
            ),
        ], style={'marginTop': '1.5%', 'marginBottom': '-2%'}),
        dbc.Row([
            dbc.Col(dbc.InputGroup(
                [
                    dbc.Input(
                        value=0.0, min=0.0, step=0.5, type='number', 
                        id='trinket_icd_precombat_1',
                    ),
                    dbc.InputGroupAddon(
                        '秒', addon_type='append'
                    ),
                ],
                id="trinket_icd_group_1"
            )),
            dbc.Col(dbc.InputGroup(
                [
                    dbc.Input(
                        value=0.0, min=0.0, step=0.5, type='number', 
                        id='trinket_icd_precombat_2',
                    ),
                    dbc.InputGroupAddon(
                        '秒', addon_type='append'
                    ),
                ],
                id="trinket_icd_group_2"
            )),
        ]),
    ], id="trinket_icd_section"),
    dbc.Tooltip(
        """Putting a trinket on ICD (internal cooldown) will prevent the trinket
            from activating until its cooldown has ended. This can be useful when
            attempting to line up trinket procs with other combat effects. Typically
            done by equipping trinkets before combat.""",
        target="trinket_icd_section"
    ),
    html.Div(
        '*确保你的配装文件里没有选神像和饰品,不然属性会错',
        style={
            'marginTop': '2.5%', 'fontSize': 'large', 'fontWeight': 'bold'
        },
    ),
    html.Div([
        dbc.Button(
            "计算DPS", id='run_button', n_clicks=0, size='lg', color='success',
            style={
                'marginBottom': '10%', 'fontSize': 'large', 'marginTop': '10%',
                'display': 'inline-block'
            }
        ),
        html.Div(
            '', id='status',
            style={
                'display': 'inline-block', 'fontWeight': 'bold',
                'marginLeft': '10%', 'fontSize': 'large'
            }
        )
    ]),
    dcc.Interval(id='interval', interval=500),
], width='auto', style={'marginBottom': '20px', 'marginLeft': '10px'})

input_layout = html.Div(children=[
    html.H1(
        children='Nerd Ecat Sims WLK猫德模拟器 v3.3',
        style={'textAlign': 'center'}
    ),
    html.H5(
        children='Nerdegghead授权 范克瑞斯Espeon翻译/编译',
        style={'textAlign': 'center', "color": 'yellow'}
    ),
    html.H5(
        children='2023.05.02',
        style={'textAlign': 'center', "color": 'red'}
    ),
    dbc.Row(
        [stat_input, buffs_1, encounter_details, iteration_input],
        style={'marginTop': '30px', 'marginBottom': '30px'}
    ),
])

stats_output = dbc.Col(
    [html.H4('Buff后属性'),
     html.Div([
         html.Div(
             '平砍速度',
             style={'width': '50%', 'display': 'inline-block',
                    'fontWeight': 'bold', 'fontSize': 'large'}
         ),
         html.Div(
             '',
             style={'width': '50%', 'display': 'inline-block',
                    'fontSize': 'large'},
             id='buffed_swing_timer'
         )
     ]),
     html.Div([
         html.Div(
             '攻强',
             style={'width': '50%', 'display': 'inline-block',
                    'fontWeight': 'bold', 'fontSize': 'large'}
         ),
         html.Div(
             '',
             style={'width': '50%', 'display': 'inline-block',
                    'fontSize': 'large'},
             id='buffed_attack_power'
         )
     ]),
     html.Div([
         html.Div(
             '破甲等级:',
             style={'width': '50%', 'display': 'inline-block',
                    'fontWeight': 'bold', 'fontSize': 'large'}
         ),
         html.Div(
             '',
             style={'width': '50%', 'display': 'inline-block',
                    'fontSize': 'large'},
             id='buffed_arp'
         )
     ]),
     html.Div([
         html.Div(
             '83级BOSS暴击:',
             style={'width': '50%', 'display': 'inline-block',
                    'fontWeight': 'bold', 'fontSize': 'large'}
         ),
         html.Div(
             '',
             style={'width': '50%', 'display': 'inline-block',
                    'fontSize': 'large'},
             id='buffed_crit'
         )
     ]),
     html.Div([
         html.Div(
             '未命中率',
             style={'width': '50%', 'display': 'inline-block',
                    'fontWeight': 'bold', 'fontSize': 'large'}
         ),
         html.Div(
             '',
             style={'width': '50%', 'display': 'inline-block',
                    'fontSize': 'large'},
             id='buffed_miss'
         )
     ]),
     html.Div([
         html.Div(
             '蓝量',
             style={'width': '50%', 'display': 'inline-block',
                    'fontWeight': 'bold', 'fontSize': 'large'}
         ),
         html.Div(
             '',
             style={'width': '50%', 'display': 'inline-block',
                    'fontSize': 'large'},
             id='buffed_mana'
         )
     ]),
     html.Div([
         html.Div(
             '智力',
             style={'width': '50%', 'display': 'inline-block',
                    'fontWeight': 'bold', 'fontSize': 'large'}
         ),
         html.Div(
             '',
             style={'width': '50%', 'display': 'inline-block',
                    'fontSize': 'large'},
             id='buffed_int'
         )
     ]),
     html.Div([
         html.Div(
             '精神',
             style={'width': '50%', 'display': 'inline-block',
                    'fontWeight': 'bold', 'fontSize': 'large'}
         ),
         html.Div(
             '',
             style={'width': '50%', 'display': 'inline-block',
                    'fontSize': 'large'},
             id='buffed_spirit'
         )
     ]),
     html.Div([
         html.Div(
             'MP5',
             style={'width': '50%', 'display': 'inline-block',
                    'fontWeight': 'bold', 'fontSize': 'large'}
         ),
         html.Div(
             '',
             style={'width': '50%', 'display': 'inline-block',
                    'fontSize': 'large'},
             id='buffed_mp5'
         )
     ])],
    width=4, xl=3, style={'marginLeft': '2.5%', 'marginBottom': '2.5%'}
)

sim_output = dbc.Col([
    html.H4('模拟结果'),
    dcc.Loading(children=html.Div([
        html.Div(
            'DPS范围',
            style={
                'width': '50%', 'display': 'inline-block',
                'fontWeight': 'bold', 'fontSize': 'large'
            }
        ),
        html.Div(
            '',
            style={
                'width': '50%', 'display': 'inline-block', 'fontSize': 'large'
            },
            id='mean_std_dps'
        ),
    ]), id='loading_1', type='default'),
    dcc.Loading(children=html.Div([
        html.Div(
            '中位数DPS',
            style={
                'width': '50%', 'display': 'inline-block',
                'fontWeight': 'bold', 'fontSize': 'large'
            }
        ),
        html.Div(
            '',
            style={
                'width': '50%', 'display': 'inline-block', 'fontSize': 'large'
            },
            id='median_dps'
        ),
    ]), id='loading_2', type='default'),
    dcc.Loading(children=html.Div([
        html.Div(
            '空蓝时间',
            style={
                'width': '50%', 'display': 'inline-block',
                'fontWeight': 'bold', 'fontSize': 'large'
            }
        ),
        html.Div(
            '',
            style={
                'width': '50%', 'display': 'inline-block', 'fontSize': 'large'
            },
            id='time_to_oom'
        ),
    ]), id='loading_oom_time', type='default'),
    html.Br(),
    html.H5('DPS占比'),
    dcc.Loading(children=dbc.Table([
        html.Thead(html.Tr([
            html.Th('技能'), html.Th('施法次数'), html.Th('CPM'),
            html.Th('平均伤害'), html.Th('DPS占比')
        ])),
        html.Tbody(id='dps_breakdown_table')
    ]), id='loading_3', type='default'),
    html.Br(),
    html.H5('触发数据'),
    dcc.Loading(children=dbc.Table([
        html.Thead(html.Tr([
            html.Th('触发类型'), html.Th('触发次数'),
            html.Th('触发覆盖'),
        ])),
        html.Tbody(id='aura_breakdown_table')
    ]), id='loading_auras', type='default'),
    html.Br(),
    html.Br()
], style={'marginLeft': '2.5%', 'marginBottom': '2.5%'}, width=4, xl=3)

weights_section = dbc.Col([
    html.H4('属性权重分析(15万以上样本)'),
    html.Div([
        dbc.Row(
            [
                dbc.Col(dbc.Button(
                    '计算属性权重', id='weight_button', n_clicks=0,
                    color='info'
                ), width='auto'),
                dbc.Col(
                    [
                        dbc.FormGroup(
                            [
                                dbc.Checkbox(
                                    id='epic_gems',
                                    className='form-check-input', checked=False
                                ),
                                dbc.Label(
                                    '装备配紫色宝石',
                                    html_for='epic_gems',
                                    className='form-check-label'
                                )
                            ],
                            check=True
                        ),
                    ],
                    width='auto'
                )
            ]
        ),
        html.Div(
            '计算权重会花很多时间,点击前请注意!',
            style={'fontWeight': 'bold'},
        ),
        dcc.Loading(
            children=[
                html.P(
                    children=[
                        html.Strong(
                            'Error: ', style={'fontSize': 'large'},
                            id='error_str'
                        ),
                        html.Span(
                            '你至少需要20000次样本才能计算权重,请修改你的样本数量',
                            style={'fontSize': 'large'}, id='error_msg'
                        )
                    ],
                    style={'marginTop': '4%'},
                ),
                dbc.Table([
                    html.Thead(html.Tr([
                        html.Th('Stat Increment'), html.Th('DPS Added'),
                        html.Th('Normalized Weight')
                    ])),
                    html.Tbody(id='stat_weight_table'),
                ]),
                html.Div(
                    html.A(
                        'Seventy Upgrades 导出权重',
                        href='https://seventyupgrades.com', target='_blank'
                    ),
                    id='import_link'
                )
            ],
            id='loading_4', type='default'
        ),
    ]),
], style={'marginLeft': '5%', 'marginBottom': '2.5%'}, width=4, xl=3)

sim_section = dbc.Row(
    [stats_output, sim_output, weights_section]
)

graph_section = html.Div([
    dbc.Row(
        [
            dbc.Col(
                dbc.Button(
                    "生成输出循环报告", id='graph_button', n_clicks=0,
                    color='info',
                    style={'marginLeft': '2.5%', 'fontSize': 'large'}
                ),
                width='auto'
            ),
            dbc.Col(
                dbc.FormGroup(
                    [
                        dbc.Checkbox(
                            id='show_whites', className='form-check-input'
                        ),
                        dbc.Label(
                            '显示平砍', html_for='show_whites',
                            className='form-check-label'
                        )
                    ],
                    check=True
                ),
                width='auto'
            )
        ]
    ),
    html.H4(
        '战斗能量变化', style={'textAlign': 'center'}
    ),
    dcc.Graph(id='energy_flow'),
    html.Br(),
    dbc.Col(
        [
            html.H5('施法顺序'),
            dbc.Table([
                html.Thead(html.Tr([
                    html.Th('时间戳'), html.Th('技能'), html.Th('状态'),
                    html.Th('能量值'), html.Th('星'),
                    html.Th('蓝量'), html.Th('怒气')
                ])),
                html.Tbody(id='combat_log')
            ])
        ],
        width=5, xl=4, style={'marginLeft': '2.5%'}
    )
])

app.layout = html.Div([
    input_layout, sim_section, graph_section
])


# Helper functions used in master callback
def process_trinkets(
        trinket_1, trinket_2, player, ap_mod, stat_mod, haste_multiplier,
        cd_delay, trinket_icd_precombat_1, trinket_icd_precombat_2
):
    proc_trinkets = []
    all_trinkets = []

    for slot, trinket in enumerate([trinket_1, trinket_2]):
        if trinket == 'none':
            continue

        trinket_params = copy.deepcopy(trinkets.trinket_library[trinket])

        for stat, increment in trinket_params['passive_stats'].items():
            if stat == 'intellect':
                increment *= 1.2  # hardcode the HotW 20% increase
            if stat in ['strength', 'agility', 'intellect', 'spirit']:
                increment *= stat_mod
            if stat == 'strength':
                increment *= 2
                stat = 'attack_power'
            if stat == 'agility':
                stat = 'attack_power'
                # additionally modify crit here
                setattr(
                    player, 'crit_chance',
                    getattr(player, 'crit_chance') + increment / 83.33 / 100.
                )
                player.agility += increment
            if stat == 'attack_power':
                increment *= ap_mod
            if stat == 'haste_rating':
                new_haste_rating = increment + sim_utils.calc_haste_rating(
                    player.swing_timer, multiplier=haste_multiplier
                )
                new_swing_timer = sim_utils.calc_swing_timer(
                    new_haste_rating, multiplier=haste_multiplier
                )
                player.swing_timer = new_swing_timer
                continue

            setattr(player, stat, getattr(player, stat) + increment)

        if trinket_params['type'] == 'passive':
            continue

        active_stats = trinket_params['active_stats']

        if active_stats['stat_name'] == 'attack_power':
            active_stats['stat_increment'] *= ap_mod
        if active_stats['stat_name'] == 'Agility':
            active_stats['stat_name'] = [
                'agility', 'attack_power', 'crit_chance'
            ]
            agi_increment = active_stats['stat_increment']
            active_stats['stat_increment'] = np.array([
                stat_mod * agi_increment,
                stat_mod * agi_increment * ap_mod,
                stat_mod * agi_increment/83.33/100.
            ])
        if active_stats['stat_name'] == 'Strength':
            active_stats['stat_name'] = 'attack_power'
            active_stats['stat_increment'] *= 2 * stat_mod * ap_mod

        if trinket_params['type'] == 'activated':
            # If this is the second trinket slot and the first trinket was also
            # activated, then we need to enforce an activation delay due to the
            # shared cooldown. For now we will assume that the shared cooldown
            # is always equal to the duration of the first trinket's proc.
            if all_trinkets and (not proc_trinkets):
                delay = cd_delay + all_trinkets[-1].proc_duration
            else:
                delay = cd_delay

            all_trinkets.append(
                trinkets.ActivatedTrinket(delay=delay, **active_stats)
            )
        else:
            proc_type = active_stats.pop('proc_type')

            if proc_type == 'chance_on_hit':
                proc_chance = active_stats.pop('proc_rate')
                active_stats['chance_on_hit'] = proc_chance
                active_stats['chance_on_crit'] = proc_chance
            elif proc_type == 'chance_on_crit':
                active_stats['chance_on_hit'] = 0.0
                active_stats['chance_on_crit'] = active_stats.pop('proc_rate')
            elif proc_type == 'ppm':
                ppm = active_stats.pop('proc_rate')
                active_stats['chance_on_hit'] = ppm/60.
                active_stats['yellow_chance_on_hit'] = ppm/60.

            if slot == 0:
                icd_precombat = trinket_icd_precombat_1
            else:
                icd_precombat = trinket_icd_precombat_2

            if trinket == 'dbw':
                trinket_obj = trinkets.DeathbringersWill(
                    stat_mod, ap_mod, icd_precombat=icd_precombat,
                    **active_stats
                )
            elif trinket_params['type'] == 'instant_damage':
                trinket_obj = trinkets.InstantDamageProc(
                    **active_stats, icd_precombat=icd_precombat
                )
            elif trinket_params['type'] == 'refreshing_proc':
                trinket_obj = trinkets.RefreshingProcTrinket(**active_stats)
            elif trinket_params['type'] == 'stacking_proc':
                trinket_obj = trinkets.StackingProcTrinket(**active_stats)
            else:
                trinket_obj = trinkets.ProcTrinket(
                    **active_stats, icd_precombat=icd_precombat
                )

            all_trinkets.append(trinket_obj)
            proc_trinkets.append(all_trinkets[-1])

    player.proc_trinkets = proc_trinkets
    return all_trinkets


def create_player(
        buffed_agility, buffed_attack_power, buffed_hit, buffed_spell_hit, buffed_crit,
        buffed_spell_crit, buffed_weapon_damage, haste_rating, expertise_rating, 
        armor_pen_rating, buffed_mana_pool, buffed_int, buffed_spirit, buffed_mp5, 
        weapon_speed, unleashed_rage, kings, raven_idol, other_buffs, stat_debuffs,
        cooldowns, bonuses, binary_talents, naturalist, feral_aggression,
        savage_fury, potp, predatory_instincts, improved_mangle, imp_motw, furor,
        natural_shapeshifter, ilotp, potion, gotw_targets
):
    """Takes in raid buffed player stats from Eighty Upgrades, modifies them
    based on boss debuffs and miscellaneous buffs not captured by Eighty
    Upgrades, and instantiates a Player object with those stats."""

    # Swing timer calculation is independent of other buffs. First we add up
    # the haste rating from all the specified haste buffs
    buffed_haste_rating = haste_rating
    haste_multiplier = (
        (1 + 0.2 * ('major_haste' in other_buffs))
        * (1 + 0.03 * ('minor_haste' in other_buffs))
    )
    buffed_swing_timer = sim_utils.calc_swing_timer(
        buffed_haste_rating, multiplier=haste_multiplier
    )

    # Also calculate hasted spell GCD for use when flowershifting
    spell_haste_multiplier = (
        (1 + 0.03 * ('minor_haste' in other_buffs))
        * (1 + 0.05 * ('spell_haste' in other_buffs))
    )

    # Augment secondary stats as needed
    ap_mod = 1.1 * (1 + 0.1 * unleashed_rage)
    debuff_ap = 0
    encounter_crit = (
        buffed_crit + 3 * ('jotc' in stat_debuffs)
        + (28 * ('be_chain' in other_buffs) + 40 * bool(raven_idol)) / 45.91
    )
    encounter_spell_crit = (
        buffed_spell_crit + 3 * ('jotc' in stat_debuffs)
        + 5 * ('shadow_mastery' in stat_debuffs)
        + (28 * ('be_chain' in other_buffs) + 40 * bool(raven_idol)) / 45.91
    )
    encounter_hit = buffed_hit
    encounter_spell_hit = (buffed_spell_hit + 3 * ('misery' in stat_debuffs))
    encounter_mp5 = (
        buffed_mp5 + 0.01 * buffed_mana_pool * ('replenishment' in other_buffs)
    )

    # Calculate bonus damage parameters
    encounter_weapon_damage = buffed_weapon_damage
    damage_multiplier = (
        (1 + 0.02 * int(naturalist))
        * (1 + 0.03 * ('sanc_aura' in other_buffs))
    )
    spell_damage_multiplier = (1 + 0.03 * ('sanc_aura' in other_buffs))
    shred_bonus = 203 * ('shred_idol' in bonuses)
    rip_bonus = 21 * ('rip_idol' in bonuses)

    # Create and return a corresponding Player object
    player = player_class.Player(
        attack_power=buffed_attack_power, ap_mod=ap_mod,
        agility=buffed_agility, hit_chance=encounter_hit / 100, 
        spell_crit_chance=encounter_spell_crit / 100,
        spell_hit_chance=encounter_spell_hit / 100,
        expertise_rating=expertise_rating, crit_chance=encounter_crit / 100,
        swing_timer=buffed_swing_timer, mana=buffed_mana_pool,
        intellect=buffed_int, spirit=buffed_spirit, mp5=encounter_mp5,
        omen='omen' in binary_talents,
        primal_gore='primal_gore' in binary_talents,
        feral_aggression=int(feral_aggression), savage_fury=int(savage_fury),
        potp=int(potp), predatory_instincts=int(predatory_instincts),
        improved_mangle=int(improved_mangle), furor=int(furor),
        natural_shapeshifter=int(natural_shapeshifter),
        ilotp=int(ilotp), weapon_speed=weapon_speed,
        bonus_damage=encounter_weapon_damage, multiplier=damage_multiplier,
        spell_damage_multiplier=spell_damage_multiplier,
        jow='jow' in stat_debuffs, armor_pen_rating=armor_pen_rating,
        t6_2p='t6_2p' in bonuses, t6_4p='t6_4p' in bonuses,
        t7_2p='t7_2p' in bonuses, t8_2p='t8_2p' in bonuses,
        t8_4p='t8_4p' in bonuses, t9_2p='t9_2p' in bonuses,
        t9_4p='t9_4p' in bonuses, t10_2p='t10_2p' in bonuses, 
        t10_4p='t10_4p' in bonuses, wolfshead='wolfshead' in bonuses,
        mangle_glyph='mangle_glyph' in bonuses,
        meta='meta' in bonuses, rune='rune' in cooldowns,
        shred_bonus=shred_bonus, rip_bonus=rip_bonus, debuff_ap=debuff_ap,
        roar_glyph='roar_glyph' in bonuses,
        berserk_glyph='berserk_glyph' in bonuses,
        rip_glyph='rip_glyph' in bonuses, shred_glyph='shred_glyph' in bonuses,
        gotw_targets=int(gotw_targets)
    )
    player.update_spell_gcd(
        buffed_haste_rating, multiplier=spell_haste_multiplier
    )
    stat_mod = (1 + 0.1 * kings) * 1.06 * (1 + 0.01 * imp_motw)
    return player, ap_mod, stat_mod, haste_multiplier


def apply_buffs(
        unbuffed_ap, unbuffed_strength, unbuffed_agi, unbuffed_hit, 
        unbuffed_spell_hit, unbuffed_crit, unbuffed_spell_crit,
        unbuffed_arp, unbuffed_mana, unbuffed_int, unbuffed_spirit, 
        unbuffed_mp5, weapon_damage, raid_buffs, consumables, imp_motw
):
    """Takes in unbuffed player stats, and turns them into buffed stats based
    on specified consumables and raid buffs. This function should only be
    called if the "Buffs" option is not checked in the exported file from
    Eighty Upgrades, or else the buffs will be double counted!"""

    # Determine "raw" AP, crit, and mana not from Str/Agi/Int
    raw_ap_unbuffed = unbuffed_ap / 1.1 - 2 * unbuffed_strength - unbuffed_agi
    raw_crit_unbuffed = unbuffed_crit - unbuffed_agi / 83.33
    raw_spell_crit_unbuffed = unbuffed_spell_crit - unbuffed_int / 166.67
    raw_mana_unbuffed = unbuffed_mana - 15 * unbuffed_int

    # Augment all base stats based on specified buffs
    gear_multi = 1.06 * (1 + 0.01 * imp_motw)
    stat_multiplier = 1 + 0.1 * ('kings' in raid_buffs)
    added_stats = 51 * ('motw' in raid_buffs)

    buffed_strength = stat_multiplier * (unbuffed_strength + gear_multi * (
        added_stats + 155 * ('str_totem' in raid_buffs)
        + 40 * ('str_food' in consumables)
    ))
    buffed_agi = stat_multiplier * (unbuffed_agi + gear_multi * (
        added_stats + 155 * ('str_totem' in raid_buffs)
        + 40 * ('agi_food' in consumables)
    ))
    buffed_int = stat_multiplier * (unbuffed_int + 1.2 * gear_multi * (
        added_stats + 60 * ('ai' in raid_buffs)
    ))
    buffed_spirit = stat_multiplier * (unbuffed_spirit + gear_multi * (
        added_stats + 80 * ('spirit' in raid_buffs)
    ))

    # Now augment secondary stats
    ap_mod = 1.1 * (1 + 0.1 * ('unleashed_rage' in raid_buffs))
    buffed_attack_power = ap_mod * (
        raw_ap_unbuffed + 2 * buffed_strength + buffed_agi
        + 550 * 1.25 * ('might' in raid_buffs) + 180 * ('flask' in consumables)
    )
    added_crit_rating = 14 * ('weightstone' in consumables)
    buffed_crit = (
        raw_crit_unbuffed + buffed_agi / 83.33 + added_crit_rating / 45.91
    )
    buffed_spell_crit = (
        raw_spell_crit_unbuffed + buffed_int / 166.67 
        + added_crit_rating / 45.91 + 5 * ('moonkin_aura' in raid_buffs)
    )
    buffed_hit = (
        unbuffed_hit + 1 * ('heroic_presence' in raid_buffs)
        + 40 / 32.79 * ('hit_food' in consumables)
    )
    buffed_spell_hit = (
        unbuffed_spell_hit + 1 * ('heroic_presence' in raid_buffs) \
            + 40 / 26.23 * ('hit_food' in consumables)
    )
    buffed_mana_pool = raw_mana_unbuffed + buffed_int * 15
    buffed_mp5 = unbuffed_mp5 + 110 * ('wisdom' in raid_buffs)
    buffed_weapon_damage = (
        12 * ('weightstone' in consumables) + weapon_damage
    )
    buffed_arp = unbuffed_arp + 40 * ('arp_food' in consumables)

    return {
        'strength': buffed_strength,
        'agility': buffed_agi,
        'intellect': buffed_int,
        'spirit': buffed_spirit,
        'attackPower': buffed_attack_power,
        'crit': buffed_crit,
        'spellCrit': buffed_spell_crit,
        'hit': buffed_hit,
        'spellHit': buffed_spell_hit,
        'weaponDamage': buffed_weapon_damage,
        'mana': buffed_mana_pool,
        'mp5': buffed_mp5,
        'armorPenRating': buffed_arp
    }


def run_sim(sim, num_replicates):
    # Run the sim for the specified number of replicates
    dps_vals, dmg_breakdown, aura_stats, oom_times = sim.run_replicates(
        num_replicates, detailed_output=True
    )

    # Consolidate DPS statistics
    avg_dps = np.mean(dps_vals)
    mean_dps_str = '%.1f +/- %.1f' % (avg_dps, np.std(dps_vals))
    median_dps_str = '%.1f' % np.median(dps_vals)

    # Consolidate mana statistics
    avg_oom_time = np.mean(oom_times)

    if avg_oom_time > sim.fight_length - 1:
        oom_time_str = 'none'
    else:
        oom_time_str = (
            '%d +/- %d seconds' % (avg_oom_time, np.std(oom_times))
        )

    # Create DPS breakdown table
    dps_table = []

    for ability in dmg_breakdown:
        if ability in ['Claw']:
            continue

        ability_dps = dmg_breakdown[ability]['damage'] / sim.fight_length
        ability_cpm = dmg_breakdown[ability]['casts'] / sim.fight_length * 60.
        ability_dpct = ability_dps * 60. / ability_cpm if ability_cpm else 0.
        dps_table.append(html.Tr([
            html.Td(ability),
            html.Td('%.3f' % dmg_breakdown[ability]['casts']),
            html.Td('%.1f' % ability_cpm),
            html.Td('%.0f' % ability_dpct),
            html.Td('%.1f%%' % (ability_dps / avg_dps * 100))
        ]))

    # Create Aura uptime table
    aura_table = []

    for row in aura_stats:
        aura_table.append(html.Tr([
            html.Td(row[0]),
            html.Td('%.3f' % row[1]),
            html.Td('%.1f%%' % (row[2] * 100))
        ]))

    return (
        avg_dps,
        (mean_dps_str, median_dps_str, oom_time_str, dps_table, aura_table),
    )


def calc_weights(
        sim, num_replicates, avg_dps, time_to_oom, kings, unleashed_rage,
        epic_gems, imp_motw
):
    # Check that sufficient iterations are used for convergence.
    if num_replicates < 20000:
        error_msg = (
            'Stat weight calculation requires the simulation to be run with at'
            ' least 20,000 replicates.'
        )
        return 'Error: ', error_msg, [], ''

    # Do fresh weights calculation
    weights_table = []

    # Calculate DPS increases and weights
    stat_multiplier = (1 + 0.1 * kings) * 1.06 * (1 + 0.01 * imp_motw)
    dps_deltas, stat_weights = sim.calc_stat_weights(
        num_replicates, base_dps=avg_dps, agi_mod=stat_multiplier
    )

    # Parse results
    for stat in dps_deltas:
        if stat == '1 AP':
            weight = 1.0
            dps_per_AP = dps_deltas[stat]
        else:
            weight = stat_weights[stat]

        weights_table.append(html.Tr([
            html.Td(stat),
            html.Td('%.2f' % dps_deltas[stat]),
            html.Td('%.2f' % weight),
        ]))

    # Generate 80upgrades import link for raw stats
    url = sim_utils.gen_import_link(
        stat_weights, multiplier=stat_multiplier, epic_gems=epic_gems
    )
    link = html.A('Eighty Upgrades Import Link', href=url, target='_blank')

    return 'Stat Breakdown', '', weights_table, link


def plot_new_trajectory(sim, show_whites):
    t_vals, _, energy_vals, cp_vals, _, _, log = sim.run(log=True)
    t_fine = np.linspace(0, sim.fight_length, 10000)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=t_fine, y=sim_utils.piecewise_eval(t_fine, t_vals, energy_vals),
        line=dict(color="#d62728")
    ))
    fig.add_trace(go.Scatter(
        x=t_fine, y=sim_utils.piecewise_eval(t_fine, t_vals, cp_vals),
        line=dict(color="#9467bd", dash='dash'), yaxis='y2'
    ))
    fig.update_layout(
        xaxis=dict(title='Time (seconds)'),
        yaxis=dict(
            title='Energy', titlefont=dict(color='#d62728'),
            tickfont=dict(color='#d62728')
        ),
        yaxis2=dict(
            title='Combo points', titlefont=dict(color='#9467bd'),
            tickfont=dict(color='#9467bd'), anchor='x', overlaying='y',
            side='right'
        ),
        showlegend=False,
    )

    # Create combat log table
    log_table = []

    if not show_whites:
        parsed_log = [row for row in log if row[1] != 'melee']
    else:
        parsed_log = log

    for row in parsed_log:
        log_table.append(html.Tr([
            html.Td(entry) for entry in row
        ]))

    return fig, log_table


# Master callback function
@app.callback(
    Output('upload_status', 'children'),
    Output('upload_status', 'style'),
    Output('buff_section', 'is_open'),
    Output('buffed_swing_timer', 'children'),
    Output('buffed_attack_power', 'children'),
    Output('buffed_arp', 'children'),
    Output('buffed_crit', 'children'),
    Output('buffed_miss', 'children'),
    Output('buffed_mana', 'children'),
    Output('buffed_int', 'children'),
    Output('buffed_spirit', 'children'),
    Output('buffed_mp5', 'children'),
    Output('mean_std_dps', 'children'),
    Output('median_dps', 'children'),
    Output('time_to_oom', 'children'),
    Output('dps_breakdown_table', 'children'),
    Output('aura_breakdown_table', 'children'),
    Output('error_str', 'children'),
    Output('error_msg', 'children'),
    Output('stat_weight_table', 'children'),
    Output('import_link', 'children'),
    Output('energy_flow', 'figure'),
    Output('combat_log', 'children'),
    Input('upload-data', 'contents'),
    Input('consumables', 'value'),
    Input('raid_buffs', 'value'),
    Input('other_buffs', 'value'),
    Input('raven_idol', 'value'),
    Input('stat_debuffs', 'value'),
    Input('imp_motw', 'value'),
    Input('trinket_1', 'value'),
    Input('trinket_2', 'value'),
    Input('trinket_icd_precombat_1', 'value'),
    Input('trinket_icd_precombat_2', 'value'),
    Input('run_button', 'n_clicks'),
    Input('weight_button', 'n_clicks'),
    Input('graph_button', 'n_clicks'),
    State('hot_uptime', 'value'),
    State('potion', 'value'),
    State('bonuses', 'value'),
    State('binary_talents', 'value'),
    State('feral_aggression', 'value'),
    State('savage_fury', 'value'),
    State('potp', 'value'),
    State('predatory_instincts', 'value'),
    State('improved_mangle', 'value'),
    State('furor', 'value'),
    State('naturalist', 'value'),
    State('natural_shapeshifter', 'value'),
    State('ilotp', 'value'),
    State('fight_length', 'value'),
    State('boss_armor', 'value'),
    State('num_targets', 'value'),
    State('boss_debuffs', 'value'),
    State('cooldowns', 'value'),
    State('rip_cp', 'value'),
    State('bite_cp', 'value'),
    State('cd_delay', 'value'),
    State('min_roar_offset', 'value'),
    State('roar_clip_leeway', 'value'),
    State('use_rake', 'value'),
    State('mangle_spam', 'value'),
    State('use_biteweave', 'value'),
    State('bite_model', 'value'),
    State('bite_time', 'value'),
    State('bear_mangle', 'value'),
    State('prepop_berserk', 'value'),
    State('preproc_omen', 'value'),
    State('bearweave', 'value'),
    State('berserk_bite_thresh', 'value'),
    State('berserk_ff_thresh', 'value'),
    State('max_ff_delay', 'value'),
    State('lacerate_prio', 'value'),
    State('lacerate_time', 'value'),
    State('powerbear', 'value'),
    State('snek', 'value'),
    State('flowershift', 'value'),
    State('gotw_targets', 'value'),
    State('daggerweave', 'value'),
    State('dagger_ep_loss', 'value'),
    State('num_replicates', 'value'),
    State('latency', 'value'),
    State('epic_gems', 'checked'),
    State('show_whites', 'checked'))
def compute(
        json_file, consumables, raid_buffs, other_buffs, raven_idol,
        stat_debuffs, imp_motw, trinket_1, trinket_2, trinket_icd_precombat_1, 
        trinket_icd_precombat_2, run_clicks, 
        weight_clicks, graph_clicks, hot_uptime, potion, bonuses,
        binary_talents, feral_aggression, savage_fury, potp,
        predatory_instincts, improved_mangle, furor, naturalist,
        natural_shapeshifter, ilotp, fight_length, boss_armor, num_targets,
        boss_debuffs, cooldowns, rip_cp, bite_cp, cd_delay,
        min_roar_offset, roar_clip_leeway, use_rake, mangle_spam,
        use_biteweave, bite_model, bite_time, bear_mangle, prepop_berserk,
        preproc_omen, bearweave, berserk_bite_thresh, berserk_ff_thresh,
        max_ff_delay, lacerate_prio, lacerate_time, powerbear, snek,
        flowershift, gotw_targets, daggerweave, dagger_ep_loss, num_replicates,
        latency, epic_gems, show_whites
):
    ctx = dash.callback_context

    # Parse input stats JSON
    imp_motw = int(imp_motw)
    buffs_present = False
    use_default_inputs = True

    if json_file is None:
        upload_output = (
            '没有选择文件,正在使用默认属性',
            {'color': '#E59F3A', 'width': 300}, True
        )
    else:
        try:
            content_type, content_string = json_file.split(',')
            decoded = base64.b64decode(content_string)
            input_json = json.load(io.StringIO(decoded.decode('utf-8')))
            buffs_present = input_json['exportOptions']['buffs']
            catform_checked = (
                ('form' in input_json['exportOptions'])
                and (input_json['exportOptions']['form'] == 'cat')
            )

            if not catform_checked:
                upload_output = (
                    '文件错误,确保你导出时选择了Cat Form',
                    {'color': '#D35845', 'width': 300}, True
                )
            elif buffs_present:
                pot_present = False

                for entry in input_json['consumables']:
                    if 'Potion' in entry['name']:
                        pot_present = True

                if pot_present:
                    upload_output = (
                        '文件错误,确保你没有选择药水',
                        {'color': '#D35845', 'width': 300}, True
                    )
                else:
                    upload_output = (
                        '文件导入成功,你选择的Buff和药水也会被导入',
                        {'color': '#5AB88F', 'width': 300}, False
                    )
                    use_default_inputs = False
            else:
                upload_output = (
                    '文件导入成功,在模拟器里选择药水和Buff',
                    {'color': '#5AB88F', 'width': 300}, True
                )
                use_default_inputs = False
        except Exception:
            upload_output = (
                '文件错误!正在使用默认属性'
                'instead.',
                {'color': '#D35845', 'width': 300}, True
            )

    if use_default_inputs:
        input_stats = copy.copy(default_input_stats)
        buffs_present = False
    else:
        input_stats = input_json['stats']

    # If buffs are not specified in the input file, then interpret the input
    # stats as unbuffed and calculate the buffed stats ourselves.
    if not buffs_present:
        input_stats.update(apply_buffs(
            input_stats['attackPower'], input_stats['strength'],
            input_stats['agility'], input_stats['hit'], input_stats["spellHit"],
            input_stats['crit'], input_stats['spellCrit'], input_stats.get('armorPenRating', 0), 
            input_stats['mana'], input_stats['intellect'], input_stats['spirit'],
            input_stats.get('mp5', 0), input_stats.get('weaponDamage', 0),
            raid_buffs, consumables,imp_motw
        ))

    # Determine whether Unleashed Rage and/or Blessing of Kings are present, as
    # these impact stat weights and buff values.
    if buffs_present:
        unleashed_rage = False
        kings = False

        for buff in input_json['buffs']:
            if buff['name'] == 'Blessing of Kings':
                kings = True
            if buff['name'] == 'Unleashed Rage':
                unleashed_rage = True
    else:
        unleashed_rage = 'unleashed_rage' in raid_buffs
        kings = 'kings' in raid_buffs

    # Create Player object based on raid buffed stat inputs and talents
    player, ap_mod, stat_mod, haste_multiplier = create_player(
        input_stats['agility'], input_stats['attackPower'], input_stats['hit'],
        input_stats['spellHit'], input_stats['crit'], input_stats['spellCrit'],
        input_stats.get('weaponDamage', 0),
        input_stats.get('hasteRating', 0),
        input_stats.get('expertiseRating', 0),
        input_stats.get('armorPenRating', 0), input_stats['mana'],
        input_stats['intellect'], input_stats['spirit'],
        input_stats.get('mp5', 0), float(input_stats['mainHandSpeed']),
        unleashed_rage, kings, raven_idol, other_buffs, stat_debuffs,
        cooldowns, bonuses, binary_talents, naturalist, feral_aggression,
        savage_fury, potp, predatory_instincts, improved_mangle, imp_motw, furor,
        natural_shapeshifter, ilotp, potion, gotw_targets
    )

    # Process trinkets
    trinket_list = process_trinkets(
        trinket_1, trinket_2, player, ap_mod, stat_mod, haste_multiplier,
        cd_delay, trinket_icd_precombat_1, trinket_icd_precombat_2
    )

    # Default output is just the buffed player stats with no further calcs
    stats_output = (
        '%.3f seconds' % player.swing_timer,
        '%d' % player.attack_power,
        '%d' % player.armor_pen_rating,
        '%.2f %%' % (player.crit_chance * 100),
        '%.2f %%' % (player.miss_chance * 100),
        '%d' % player.mana_pool, '%d' % player.intellect,
        '%d' % player.spirit, '%d' % player.mp5
    )

    # Create Simulation object based on specified parameters
    bite = bool(use_biteweave)
    bite_time = None if bite_model == 'analytical' else bite_time
    rip_combos = int(rip_cp)

    if 'lust' in cooldowns:
        trinket_list.append(trinkets.Bloodlust(delay=cd_delay))
    if 'unholy_frenzy' in cooldowns:
        trinket_list.append(trinkets.UnholyFrenzy(delay=cd_delay))
    if 'shattering_throw' in cooldowns:
        trinket_list.append(trinkets.ShatteringThrow(delay=cd_delay))
    if 'wastes_idol' in bonuses:
        idol = trinkets.ProcTrinket(
            chance_on_hit=0.75, stat_name='attack_power',
            stat_increment=2 * stat_mod * ap_mod * 61, proc_duration=10,
            cooldown=10, proc_name='Snap and Snarl', shred_only=True,
            swipe_only=True
        )
        trinket_list.append(idol)
        player.proc_trinkets.append(idol)
    if 'idol_of_mutilation' in bonuses:
        idol = trinkets.RefreshingProcTrinket(
            chance_on_hit=0.70,
            stat_name=['agility', 'attack_power', 'crit_chance'],
            stat_increment=np.array([
                200. * stat_mod,
                200. * stat_mod * ap_mod,
                200. * stat_mod / 83.33 / 100.,
            ]),
            proc_duration=16, cooldown=8, proc_name='Mutilation',
            cat_mangle_only=True,
            shred_only=True
        )
        trinket_list.append(idol)
        player.proc_trinkets.append(idol)
    if 'mongoose' in bonuses:
        mongoose_ppm = 0.73
        mongoose_enchant = trinkets.RefreshingProcTrinket(
            stat_name=[
                'agility', 'attack_power', 'crit_chance', 'haste_rating'
            ],
            stat_increment=np.array([
                120. * stat_mod,
                120. * stat_mod * ap_mod,
                120. * stat_mod / 83.33 / 100.,
                30
            ]),
            proc_name='Lightning Speed', chance_on_hit=mongoose_ppm / 60.,
            yellow_chance_on_hit=mongoose_ppm / 60.,
            proc_duration=15, cooldown=0
        )
        trinket_list.append(mongoose_enchant)
        player.proc_trinkets.append(mongoose_enchant)
    if 'executioner' in bonuses:
        executioner_enchant = trinkets.RefreshingProcTrinket(
            stat_name='armor_pen_rating', stat_increment=120,
            proc_name='Executioner', chance_on_hit=1./60.,
            yellow_chance_on_hit=1./60., proc_duration=15, cooldown=0
        )
        trinket_list.append(executioner_enchant)
        player.proc_trinkets.append(executioner_enchant)
    if 'berserking' in bonuses:
        berserking_enchant = trinkets.RefreshingProcTrinket(
            stat_name='attack_power', stat_increment=400 * ap_mod,
            proc_name='Berserking', chance_on_hit=1./60.,
            yellow_chance_on_hit=1./60., proc_duration=15, cooldown=0
        )
        trinket_list.append(berserking_enchant)
        player.proc_trinkets.append(berserking_enchant)
    if 'engi_gloves' in bonuses:
        trinket_list.append(trinkets.ActivatedTrinket(
            'haste_rating', 340, 'Hyperspeed Acceleration', 12, 60,
            delay=cd_delay
        ))

    if potion == 'haste':
        trinket_list.append(trinkets.HastePotion(delay=cd_delay))

    mangle_idol = None

    if 'mangle_idol' in bonuses:
        mangle_idol = trinkets.IdolOfTheCorruptor(stat_mod, ap_mod)
        trinket_list.append(mangle_idol)
        player.proc_trinkets.append(mangle_idol)

    rake_idol = None

    if 'rake_idol' in bonuses:
        agi_gain = 44. * stat_mod
        stack_increments = np.array([
            agi_gain, agi_gain * ap_mod, agi_gain / 83.33 / 100.
        ])
        rake_idol = trinkets.StackingProcTrinket(
            stat_name=['agility', 'attack_power', 'crit_chance'],
            stat_increment=stack_increments, max_stacks=5,
            aura_name='Idol of the Crying Moon', stack_name='Agile',
            chance_on_hit=0.0, yellow_chance_on_hit=1.0, aura_duration=1e9,
            cooldown=1e9
        )
        trinket_list.append(rake_idol)

    target_count = int(round(num_targets))
    allow_bearweave = bool(bearweave) and (target_count < 3)
    sim = ccs.Simulation(
        player, fight_length + 1e-9, 0.001 * latency, boss_armor=boss_armor,
        min_combos_for_rip=rip_combos, min_combos_for_bite=int(bite_cp),
        mangle_spam=bool(mangle_spam), use_rake=bool(use_rake), use_bite=bite,
        bite_time=bite_time, bear_mangle=bool(bear_mangle),
        use_berserk='berserk' in binary_talents,
        prepop_berserk=bool(prepop_berserk), preproc_omen=bool(preproc_omen),
        bearweave=allow_bearweave, berserk_bite_thresh=berserk_bite_thresh,
        berserk_ff_thresh=berserk_ff_thresh, max_ff_delay=max_ff_delay,
        lacerate_prio=bool(lacerate_prio), lacerate_time=lacerate_time,
        powerbear=bool(powerbear), snek=bool(snek) and allow_bearweave,
        flowershift=bool(flowershift), daggerweave=bool(daggerweave),
        dagger_ep_loss=dagger_ep_loss, min_roar_offset=min_roar_offset,
        roar_clip_leeway=roar_clip_leeway, num_targets=target_count,
        trinkets=trinket_list, haste_multiplier=haste_multiplier,
        hot_uptime=hot_uptime / 100., mangle_idol=mangle_idol,
        rake_idol=rake_idol
    )
    sim.set_active_debuffs(boss_debuffs)
    player.calc_damage_params(**sim.params)

    # If either "Run" or "Stat Weights" button was pressed, then perform a
    # sim run for the specified number of replicates.
    if (ctx.triggered and
            (ctx.triggered[0]['prop_id'] in
             ['run_button.n_clicks', 'weight_button.n_clicks'])):
        avg_dps, dps_output = run_sim(sim, num_replicates)
    else:
        dps_output = ('', '', '', [], [])

    # If "Stat Weights" button was pressed, then calculate weights.
    if (ctx.triggered and
            (ctx.triggered[0]['prop_id'] == 'weight_button.n_clicks')):
        weights_output = calc_weights(
            sim, num_replicates, avg_dps, dps_output[2], kings, unleashed_rage,
            epic_gems, imp_motw
        )
    else:
        weights_output = ('Stat Breakdown', '', [], '')

    # If "Generate Example" button was pressed, do it.
    if (ctx.triggered and
            (ctx.triggered[0]['prop_id'] == 'graph_button.n_clicks')):
        example_output = plot_new_trajectory(sim, show_whites)
    else:
        example_output = ({}, [])

    return (
        upload_output + stats_output + dps_output + weights_output
        + example_output
    )


# Callbacks for disabling rotation options when inappropriate
@app.callback(
    Output('bearweave_options', 'is_open'),
    Output('biteweave_options', 'is_open'),
    Output('berserk_options', 'is_open'),
    Output('omen_options', 'is_open'),
    Output('empirical_options', 'is_open'),
    Output('lacerate_options', 'is_open'),
    Output('bearweave', 'options'),
    Output('lacerate_prio', 'options'),
    Output('flowershift', 'options'),
    Output('flowershift_options', 'is_open'),
    Output('dagger_options', 'is_open'),
    Input('bearweave', 'value'),
    Input('flowershift', 'value'),
    Input('use_biteweave', 'value'),
    Input('bite_model', 'value'),
    Input('lacerate_prio', 'value'),
    Input('daggerweave', 'value'),
    Input('binary_talents', 'value'),
    Input('num_targets', 'value'))
def disable_options(
    bearweave, flowershift, biteweave, bite_model, lacerate_prio, daggerweave,
    binary_talents, num_targets
):
    bearweave_options = {'label': '尝试精裂舞', 'value': 'bearweave'}
    flowershift_options = {
        'label': '尝试爪子舞', 'value': 'flowershift'
    }
    lacerate_options = {
        'label': ' prioritize Lacerate maintenance over Mangle',
        'value': 'lacerate_prio'
    }

    # Disable Lacerateweave and flowershift in UI given recent Blizzard changes
    flowershift_options['disabled'] = False
    bearweave_options['disabled'] = (int(round(num_targets)) > 2)
    lacerate_options['disabled'] = True

    return (
        bool(bearweave), bool(biteweave), 'berserk' in binary_talents,
        'omen' in binary_talents, bite_model == 'empirical',
        bool(lacerate_prio), [bearweave_options], [lacerate_options],
        [flowershift_options], bool(flowershift), bool(daggerweave)
    )
    
#Callback for displaying trinket ICD options when appropriate
@app.callback(
    Output('trinket_icd_text_1', 'style'),
    Output('trinket_icd_group_1', 'style'),
    Output('trinket_icd_text_2', 'style'),
    Output('trinket_icd_group_2', 'style'),
    Output('trinket_icd_precombat_1', 'value'),
    Output('trinket_icd_precombat_2', 'value'),
    Input('trinket_1', 'value'),
    Input('trinket_2', 'value'),
    Input('trinket_icd_precombat_1', 'value'),
    Input('trinket_icd_precombat_2', 'value'),)
def show_trinket_ICD_options(trinket_1, trinket_2, trinket_icd_precombat_1, trinket_icd_precombat_2):
    show_trinket_1_ICD = trinket_1 != 'none' and trinkets.trinket_library[trinket_1]['type'] in ['proc','instant_damage']
    show_trinket_2_ICD = trinket_2 != 'none' and trinkets.trinket_library[trinket_2]['type'] in ['proc','instant_damage']
    trinket_1_style = {} if show_trinket_1_ICD else {'visibility':'hidden'} 
    trinket_2_style = {} if show_trinket_2_ICD else {'visibility':'hidden'}
    if not show_trinket_1_ICD:
        trinket_icd_precombat_1 = 0
    if not show_trinket_2_ICD:
        trinket_icd_precombat_2 = 0
    return (trinket_1_style, trinket_1_style, trinket_2_style, trinket_2_style, trinket_icd_precombat_1, trinket_icd_precombat_2)

if __name__ == '__main__':
    multiprocessing.freeze_support()
    app.run_server(
        host='0.0.0.0', port=8080, debug=False
    )
