---
resource_id: METHOD-IACMR-EMPIRICAL-2018
edition_year: 2018
chapter_id: ch15
title: 第15章 结构方程模型
pdf_page_start: 483
pdf_page_end: 508
source_line_start: 9415
source_line_end: 10112
tags:
- SEM
- CFA
- measurement_model
- path_model
- fit_index
- Mplus
status: source_preserved_ocr_markdown
rights: user_supplied_private_research_copy
---

<a id="pdf-page-483"></a>
<!-- PDF页 483 -->

## 第15章 结构方程模型

张伟雄”新西兰奥克兰大学

王畅香港城市大学: > KBAR a: 15.1 什么是结构方程模型 | |: 15.2 结构方程模型的优点 | |: 15.3 测量基本概念 |: 15.4 ”测量误差: | 18.5 结构方程模型理论和刘辑 |:15.6 结构方程模型的基本类型:: 15.6.1 测量模型 i | 15.6.2 路径模型:: 15.6.3 全模型: i 15.6.4 ”均值结构模型! | 15.7 Mplus 程序撰写:

: 15.9 结构方程模型发展的新趋势 3


<a id="pdf-page-484"></a>
<!-- PDF页 484 -->

### 15.1 什么是结构方程模型

从统计学的角度来讲, 所谓模型,是以系统方式来描述观察变量 (observed variables) 和潜变量 (latent variables) 间的关系。 而本章我们要向大家介绍的结构方程模型 (structural equation modeling, SEM) 是用来检验关于观察变量和潜变量及潜变量与潜变量之间假设关系的一种多重变量统计分析方法, 即以所搜集数据来检验基于理论所建立的假设模型。 所以,SEM 是一种理论模型检定的统计方法。

理论研究中会涉及许多变量,而我们熟悉的回归方程一般只能一次解释一个因变量 (dependent variable) 和几个自变量 (independent variable) 之间的关系。 假如我们有一个以上的因变量, 便需要做多次的回归方程分析, 这个方法的缺点是未能考虑各个因变量之间的关系。 这时,包含了一连串回归方程的结构方程却恰恰可以同时分析出多个因变量与自变量自身及之间的复杂关系。 可见, 传统的统计方法需要多次处理这些变量之间的关系,而结构方程则可以做到同时同步分析, 这样,研究的准确性就会大大提高。

### 15.2 结构方程模型的优点

简单来说,结构方程具有以下优点: (1) 在管理,社会教育、 心理学的研究中许多变量都是不可直接测量的,一般称为构念。 例如,人的态度、 认知、 心理等,我们称这些变量为潜变量。 通常的做法是以观察变量来间接量度潜变量, 如用数条问卷题目答案的平均值作为潜变量的数值。 传统方法正是用问卷题目平均值来反映构念,之后代入回归方程来计算。但这些可观察的变量可能包含了测量误差,从而影响回归模型的参数估计。 一般而言, 从间卷题目得来的观察变量都是由真实值和测量误差所组成的,在有商个变Et (bi-variate) 的情况下,随机误差对估计各参数之间相关性的影响可以用公式表i = Take (15 - 1) SUE yr, FE X SY WER OP ACY AK Bs REX A OY SCP BY HE AL sr, HEX WY iE sr, EY BY gE 1 - r, 是 X 的测量误差;l - 7,, 是 Y 的测量误差。 其中由于 7,, 和 +, 的最大值取 1, 所以我们可以得到 7,,<7 的结论。 在只有两个变量的情况下,倘若已知 r,, =0.64,7r,, 和 77, 分别取 0.8, 便可应用以上的公式还原计算出


<a id="pdf-page-485"></a>
<!-- PDF页 485 -->

r=0.8, 这种方式称为减弱校正 (adjustment for attenuation)。 可是在多个变量(multi-variate) 的情况下又是怎样呢? 当自变量的个数多于一个时,测量误差对参数之间相关性的影响是不可预测的, 即有可能使其变大,但也有可能使其变小, 因此不能做出减弱校正。 这时结构方程可以帮助我们准确估计出测量误差的大小,在分析潜变量之间的结构关系时,结构方程可以吻除随机测量误差,从而大大提高了整体测量的准确度。

(2) 当我们以问卷题目或其他观察变量测量潜变量时,我们便假设了以那些观察变量来测量特定的潜变量,我们可以验证性因子分析来判断观察变量与潜变量之间的假设关系是否与数据吻合。 若结果证明我们的假设是正确的,那么其收SUSU (convergent validity) 也得到了相应的证明。 至于判别效度 (discriminant validity),我们可以通过检测各个潜变量之间的相关系数来判断。

(3) 结构方程可同时计算多个因变量之间的关系。 特别是应用于中介效应(mediating effect) 的研究,如在组织理论中,变量 4 不是直接影响到变量 8, 而是中间通过变量 C 到达的。 这时,结构方程便会给予这些问题以最综合恰当的分析

(4) 在研究中,我们也会遇到一些多层构念 (multi-dimensional/mega construct)的测量问题。 什么是多层构念? 即同时包含了不同的概念的统领因子。 例如,工作满意度就是一个多层构念,因为它下面还同时包括像对上司同事、 工作环境,薪酬.工作性质等满意程度的多重内涵。 而结构方程可以通过高阶因于(higher-order factor) 分析对此情况进行妥善处理。

### 15.3 ”测量基本概念

如前文所述,我们称那些在研究中抽象的.不可直接观察测量的变量为潜变量(latent variable), 潜变量是要通过一系列的观察变量 (observed variables) 来间接体现的。 概括来说,结构方程一方面在描述观察变量是如何测量潜变量的, 另一方面也是在表达各个潜变量之间的关系。

构念是当我们与人沟通时所表达的一个抽象的概念,如对一家餐厅的满意程度。 它是由许多具体的易于观察的变量所构成的,如餐厅的食物质量、 价格水平、服务质量环境因素等。 而通常是基于方便沟通的考虑,所以选取构念来代表所有观察变量。 当然, 随着时间和环境的改变,代表一个构念的各个观察变量也会发生变化。 那么,这时我们就要考虑到这个潜变量要用什么新的观察变量来测量的问题。 因此,这里涉及了两个方向的问题,一是不同的观察变量代表了何种构念,二


<a id="pdf-page-486"></a>
<!-- PDF页 486 -->

是一个构念又是由哪些观察变量所构成的。

以上的测量概念是结构方程的基本测量概念,一般被称为反映型测量 (reflective measure),是建基于古典真实分数模型 (classical true score model),以潜变量来推算观察变量的值, 并以推算观察变量值的误差来计算测量的信度, 而一个潜变量以下的多个观察变量需要有高的相关系数。 相反,形成型测量 (formative measure)是以观察变量来推算潜变量的值,推算潜变量值的误差不能用来计算测量的信度。严格来说,在这种情况下观察变量形成的并不是一个潜变量, 而只是一个指数 (in-

### 15.4 ”测量误差

古典真实分数模型是以真实分数及误差分数的观点来解释信度的, 即个人的观察分数 (observed scores) 是以真实分数与误差分数两部分的和组成的。 它们之间的关系可以表示为:

X=T+E (15 -2)

实际上,只有在理想和完美的测验条件下才能获得无误差的真实分数,可是这种情况很少存在。 因此,我们说任何一个测验的观察分数都包含了部分的误差成分。 这个误差是由系统误差 (systematic error) 和随机误差 (random error) 两部分组成的。 但其中的系统误差只有在一些特定的研究设计中才可以被检测出来。 因此,一般来讲, 我们假定系统误差的值等于零, 但其实它被包含在真实分数中未能体现出来。

其中,随机误差的特性有以下三点:

(1) 由于误差完全是随机的,所以一个总体的误差分数的平均值应该是零;

(2) 一个总体的真实分数和误差分数之间的相关性为零;

(3) 任何两项随机误差之间的相关性为零。

我们在结构方程中依旧保持对以上第一点和第二点的假设,而对第三点的假设则不需要一定有所支持。 那么,在何种情况下第三点假设不适合存在呢? 一般来讲, 当相同试题在同一结构方程中出现的次数大于一次时,误差之间便可能存在相关性。 简单归纳, 有以下情况:

(1) 同一试题语句对不同受访者引起的误差, 即不同受访者使用相同试题在


<a id="pdf-page-487"></a>
<!-- PDF页 487 -->

对同一测量对象测量时,对试题语句产生的误差会使其结果误差之间产生相关性。例如,在进行 360 度的绩效评估中,不同人会利用相同的测量工具, 即同一份问卷对指定的对象进行工作表现评佑。 这时,我们便会假设来自不同受访者,如调查对象本人和其上司的评价结果误差之间是有一定相关性联系的。 而这恰恰是结构方程可以测定,但一般的回归方程不能测定的。

(2) 同一试题在不同时间对同一受访者引起的误差。 这时除了有语句引起的

差,还包括同一受访者对这一误差随着时间的不断重复。 所以,相同试题在不同时间对同一个测生对宗广生的次蓉害间全站生相关性 > 如应用于纵向时间序列研3€ (longitudinal time series study),这正是传统的方法所不能很好处理的情况之一,而结构方程却可大大派上用场。

就像前面所谈到的一样,我们不可以在任何情况下都抱有随机误差之间的相关性为零的假设,但是同时也应时刻注意以下两点的影响:第一,误差之间的相关性不可随意添加,一定要有强有力的理论支持作为前提; 第二,基于理论支持,如果误差之间真正存在相关性,而我们却恰恰忽略了此相关性的存在,这时,我们的测量结果会对其他参数的估计产生很大的影响。

### 15.5 结构方程模型理论和远辑

接下来我们详细地介绍一下结构方程的概念。 如图15 - 1 所示, 虚线上面的部分代表的是总体 (population) 信息,是虚构的,而虚线下半部分则是来自样本(sample) 的真实信息。

首先我们来介绍虚线以上的来自总体的信息。 从左上角开始看起,这是来自总体数据的一些变量, 此时虽然不知道它们之间的相互关系,但是这些变量间的关系可用相关和矩阵来表示, 即提出协方差矩阵卫,,而右手边则是在基于不同假设基础上所产生的描述各变量之间关系的不同模型, 即模型 k -1kk+1。 根据不同的假设模型可以估算每个模型的近似协方差矩阵, 即王,。 这时,比较,与一; 的不同可得到 A,,,, 即总体不一致处 (population discrepancy). A,,,, Wik, 与DX, 之间越接近,继而进一步说明了之前所假设的代表变量之间关系的模型上越接近真实总体变量之间的相互关系, 即最初的操作模型 (operating model)。

下面我们再来谈谈虚线以下来自样本的信息。 就像图15 - 1 左边展示的那样,由总体到样本之间要通过抽样的过程,并且伴随误差的产生, 即总体数据 (population data) + 抽样误差 (sampling error) = FFAS ROR FEE (CY). MY Fe eT Wt


<a id="pdf-page-488"></a>
<!-- PDF页 488 -->

RISE ”结构方程模型

a名体变量 | 忆mien E22 不同的假设模型[ 描述及 oe Hi AE MZ 简化误差地 i总体信息 | A 5 描述及 | py 简化误差总体信息 EMBASE iy ogy协方差矩阵 “HE ME 描述及 BE cial shite Noe see 抽样 | 癌体 |过程样本

样本 ”不一致处估量 WA协方差拓阵 (WSR HOT EME GFI 代表)

图15 -1 结构方程模型概念图

出样本的协方差矩阵 5$。 相应地,基于假设的模型,可以产生拟合协方差甜阵呈,。

HP AHP DD, 及 4,。, 都是虚构的,实际上我们是要比较样本中的 5 与 Si的大小, 即 4,.,。 在结构方程中用不同的契合指数 (fit index) 来代表 A,, 的大小,其中最经常使用的拟合指数为 Xx (chi-square). ZEEE HORE x? 即 A. 越小, 则说明拟合

协方差矩阵三, 越接近样本协方差矩阵 5, 从而说明了我们前面所提出的模型与数据的拟合程度高。15.6 结构方程模型的基本类型

简单来说,结构方程模型可以分成以下四大类:测量模型 (measurement model)、路径模型 (path model),全模型 (full model) 和均值结构模型 (model with mean struc-

tures)。15.6.1 测量模型图15 -2 基本构造了测量模型的面貌,这里,我们用八个观察变量来测量两个

![原书图示（PDF第488页）](../images/fig-p0488-1.jpg)

![原书图示（PDF第488页）](../images/fig-p0488-2.jpg)


<a id="pdf-page-489"></a>
<!-- PDF页 489 -->

潜变量。 其中,前四个观察变量测量第一个潜变量,而后四个观察变量测量第二个潜变量。 如图15 -2 所示,这两个潜变量是相关的,而潜变量与观察变量之间的关系可表示为因子负荷 (factor loading), 即入,并且每个观察变量的测量误差用 6 来代表。 另外,在结构方程模型常用图标的表示法中, 圆或李圆表示潜变量或因子,而正方形或长方形表示观察变量。 其实,测量模型的主要用途是可以通过验证性因子分析来帮助我们检验心中的假设, 即如图15 -2 所示的因子模型是否与数据吻合,是否为一个好的模型,并同时对各因子间参数做出合理估计。 这其实对应了我们前面提到的对构念效度的检测。

2

[x | Le] Le] [x] L%] Le] Le] [x]

6, 6 6; 6, 6, 6 6, Oe

图15-2 测量模型

### 15.6.2 路径模型

如图15 -3 所示, 这个路径模型包含三个自变量和两个因变量, 它们之间有着复杂的相互关系。 简单来讲,结构方程模型可同时将所有这些关系一起估算,从而避免了当考虑一个因变量时,忽略了其他因变量存在及其影响的情况。 路经分析的主要作用是想了解各变量之间的关系,这其中包括直接关系和间接关系两大类。直接关系 (direct effect) 是指某一变量对男一变量产生直接影响,如图15 -3 中从变量 X, 到变量 Y,,或从变量 XX BAR HEY, iii fa] eK AK (indirect effect) 则是指某一变量对另一变量的影响乃是透过其他变量而形成的。 这个中间变量称为中介变量 (mediating variable),如图15 -3 示,X, 是透过了而影响了的。 综上所述:总效果 (total effect) 是指某一变量对另一变量的直接效果加上间接效果的总和。 例如, X; 与】 之间存在直接关系 ys,同时通过 Y, 也存在着间接关系 y,3B,,那么 X, 与,的总效果就是以上直接效果和间接效果之和 (yi3B,, + yw)。 昌然传统的回归性

![原书图示（PDF第489页）](../images/fig-p0489-1.jpg)


<a id="pdf-page-490"></a>
<!-- PDF页 490 -->

分析可以将变量间复杂的关系分拆成直接关系和间接关系,但是过程烦琐。 结构方程模型为我们提供了一个简单的方法, 即可同时分析各种变量之间的关系。

& Xx, Yu Bx Y,: % & P12% Yau Yu x; 15-3 ”路径模型

### 15.6.3 全模型

如图15 -4 所示, 全模型结合了测量模型和路径模型,也同时包含外源变量和内生变量的模型,也称为完整模型 (complete model)。 完整模型包含了八个基础参

SE Eh PE A, 和 A,、 路径系数矩阵和丁、 外生潜变量 & 的方差协方6, 6, 6; 6 [31 6 E4

Loe ibid

Y, Y, Yy, Y, 1 1 6 5 6 &

BH15-4 全模型

![原书图示（PDF第490页）](../images/fig-p0490-1.jpg)

![原书图示（PDF第490页）](../images/fig-p0490-2.jpg)


<a id="pdf-page-491"></a>
<!-- PDF页 491 -->

FEI ED EPEC 的方差协方差矩阵多及观测误差 6 和的方差协方差和矩阵 O,和 @,。 我们可以根据结构方程模型的四个基本和矩阵方程式, 写出八个基础参数甜阵的具体关系:

X= Aé£+6 (15 - 3) BD =A, A’, + 0, (15 -4) Y=Ante (15 -5) n = Bn+Ti+ (15 - 6)

### 15.6.4 ”均值结构模型

近三十年前,学者们对结构方程的认识只局限于协方差矩阵的形式,而现在的研究已扩展到了增加对潜变量均值的分析。 均值结构模型附加了两个基础参数和矩阵: 截距 7 和潜变量均值 «, 它们的关系可以用式 (15 -7) 的矩阵方程式表示:

Ls: = 7 + AK (15 -7)

对单一组别的结构模型来说,由于潜变量的度量单位 (scale) 及其截距 (intercept) 都是随意设定的,因此, 潜变量的均值没有很大的意义。 但是在跨组别 (crossgroup) 比较研究中,均值结构模型可用以比较各组别的潜变量均值的大小。

### 15.7 Moplus 程序撰写

目前,有多种软件可以用来分析结构方程模型,本章在这里要详细介绍的是近年比较流行的 Mplus 软件,其他流行的软件包括 AMOS EQS、R 和 LISREL。 首先,我们介绍一下潜变量的度量单位。 开篇我们提到过, 潜变量是个虚拟的概念,那么当我们要量度这些诸如认知.态度等因子时,就必然无法取用像以往量度距离的干米,或量度重量的千克这样被大家一致认可的单位进行测量。 然而,在结构方程模型中,因子一定要有自己的单位方可计算,所以,通常我们采取以下两种方法之一: (1) 固定负荷法, 即任取一个观察变量 (X,) 为参照指标, 设定其因子负荷 (factor loading) A 为 1。 这样一来, 便使得潜变量一个单位的变化相应导致其观察变量一个单位的变化。(2) 固定因子方差法:即将潜变量标准化, 设定其方差 (91,)为 1。

虽然图15 -5 两种方法在数字的表述上是不同的,但是殊途同归,本质上是相同的。 如图15 -5 所示,模型 1 采用的是固定因子方差法,将因子标准化后,四个观察变量都有其相应的因子负荷。 而模型 2 采用的是固定负荷法, 即选择了 XX 为


<a id="pdf-page-492"></a>
<!-- PDF页 492 -->

BASE ”结构方程模型

参照指标并且将其因子负荷 A 设定为 1。 换个角度分析, 其实模型 2 是将模型 1中所有的因子负荷数全部除以第一个指标 (即参照指标) 的因子负葵数 (即 0.44)从而得到了模型 2 的各个因子负荷数值,相应地,此时模型 2 中因子的方差也变成了 0.44 的平方, 即 0.1936。 综上所述, 无论我们用哪一种方法来设定潜变量的单位,所要估测的目标参数数量都是不变的,具体到本例, 模型 | 和模型 2 同样需要得到对八个参数的估测结果,这一点是不变的。 这里再特别强调一点, 当我们进行跨组别比较研究,特别是跨文化 (eross culture) 比较研究时, 则必须采用固定负荷法来完成对潜变量单位标准化这一步骤。 因为在固定方差法中,两组构念的方差(gu) 假设为相等,而这个假设尤其在跨文化比较研究中是不恰当的,所以我们选择无此假设的固定负荷法。

### 0.15 ——>|

### 0.44 模型 ]固定因子方差法

### 0.24 ——>

9-10

### 0.32 ——>

### 0.45 ——>

### 0.15 —

x,

### 1.00模型 2

固定负荷法

### 0.24 ——>|

x,

,,-0.1936

### 0.32 ——>

### 0.45 ——>}

图15 -5 设定潜变量单位的方法

在具体解释之前,我们还要先阐灵清楚一个概念:模型识别 (model identification), 即衡量有无足够的方程来解决想要估测的参数。 这个规律是这样的: 设问题涉及上个观察变量, 则协方差矩阵是一个 k 阶的对称方程,总共有 p =

![原书图示（PDF第492页）](../images/fig-p0492-1.jpg)


<a id="pdf-page-493"></a>
<!-- PDF页 493 -->

k(k+1)/2 个不重复元素。 而 gq 则代表所需估计的参数个数。 模型的自由度(degree of freedom,DF) =p -g。 在图15 -2 的例子中,该模型需要估计 6 个因子负荷.3 个因子间相关系数和 8 个变量的误差方差, 共需估计 g=17 个参数;因为有8 个变量,所以 p=8 x (8 +1)/2 =36。 这样一来,此模型的自由度 =36 - 17 =19若一个模型的自由度为 0, 即不重复元素的个数 p 等于所需估测参数个数 q, 我们称这样的模型为仅限识别模型 (just-identified model)。 它的 chi-square 等于 0, 即是完全吻合模型,同时表示我们无法衡量这个假设的模型与原始数据的吻合程度。换个角度来讲, 如果任意两个结构方程的自由度都是 0, 那么在这种情况下,它们的拟合度都是完全吻合的,也证明了理论上不同的模型可以得到相同的拟合指数。反过来,这更加说明了我们一直强调的所假设模型要给予坚实的理论依托的道理。如果自由度小于 0, 则该模型称为未识别模型 (under-identified model),这时我们的估测得不到任何结果。

在介绍了单位设定和模型识别概念之后, 接下来,我们简单介绍一下建立结构方程模型的五个步骤:

第一步, 正如前面所谈到的,结构方程中的分析统称为检定分析, 即是对假设模型的一种检定,所以我们首先应当建立一个基于理论基础的假设模型。

第二步,根据理论所表达的各变量之间的相互关系,整个模型用路径图 (path diagram) 的方式旦现。

第三步, 将前面所陈述的关系——表达成为 Mplus 的程序语言,然后运行结果。 当然,除了 Mplus, 其他软件如 AMOS、EQS、R 和 LISREL 都可以起到同样的

第四步,结果输出。 这时我们要着重观察几个方面的因素:(1) 参数估计的可行性; (2) 假设模型与实验数据的拟合程度;(3) 参数估计是否显著。

第五步, 解释输出结果。

下面,我们以验证型因子分析为例来详细解释以上步骤:

在理论基础上建立假设的模型是建立结构方程模型的第一步,也是最重要的一步。 建立结构方程模型首先是以理论基础来为各个构念之间的关系做出假设,再设定量表中各观察变量与各潜变量之间的关系。 结构方程模型只是一种统计方法,用以检验样本数据与假设模型的拟合程度。 由于不同的模型有可能得出相同的拟合协方差矩阵,因此与样本数据也有相同的拟合程度。 在这种情况下,结构方程模型不能辨别哪个假设模型比较好,而必须依赖理论基础来选择适当的模型

假设经过第一步的理论架构之后而得出两个潜变量之间存在相关性,那么,第


<a id="pdf-page-494"></a>
<!-- PDF页 494 -->

二步就是要通过路径图的形式将理论演化出来, 即如图15 -2 所示, 用八个变量来测量这两个潜变量之间的关系。 其中代表的观察变量,A 代表对 8 的因子负荷,é 代表潜变量, 而 6 则代表了 XX 的测量误差。X,.X,、X; 和 XX 测量第一个潜AB UE NX, NX, AX, 测量第二个潜变量。 此外,我们还用协方差矩阵来设定这两个潜变量之间的关系。

做好了以上的准备工作之后,我们终于开始第三步——撰写 Mplus 程序的工

Mplus 程序可主要分为下列四个部分,依次为:

(1) 输入指令 (TITLE, DATA, VARIABLE 和 DEFINE command);

(2) 分析指令 (ANALYSIS command);

(3) 模型指令 (MODEL command);

(4) 输出指令 (OUTPUT, SAVEDATA 和 PLOT command)

我们首先从输入指令开始,分别简单解释各个指令的使用方法:

输入指令:TITLE 是标题句,是自己对整个程序的描述,可超过一行;DATA 指令提供了数据输入文件的名称和位置;VARIABLE 指令提供了数据输入文件中变量的名字, 如本例中有八个变量,分别称作 Xl1、X2、X3、X4、X5、X6、X7、X8; DEFINE指令用以将现有的变量换算成新的变量,就如 SPSS 的换算 (transform) 功能。

分析指令:ANALYSIS 指令提供了分析时所需要的一些基本分析以外的特别分析功能,如分析的类型特别的模型估计方法、 自助抽样 (bootstrap) 的数目、 多层次模型潜变量的交互分析 (latent interaction) 和其他特别的运算方法。

模型指令:模型指令描述了各个变量之间的关系。 在测量模型中潜变量与观察变量之间的关系以 BY 来代表,例如, “Fl BY Xl1、X2、X3、X4" 代表了洪变量 FI以四个观察变量 XL.X2、X3.X4 来测量。 在路径模型和全模型中各个变量之间的回归关系是以 ON 来代表,例如,“73 ON Y1,X2” {R47 ER YZ LA YI Al X2 HK估计。

输出指令:0UTPUT 指令是用以要求基本结果以外的输出的,如各个估算值的标准值 (STDYX 和 STDY);SAVEDATA 指令是用以要求将各个输出结果储存在特定的档案中的;PLOT 指令是用以要求将估算结果以图像的方式来表达的。

现在,我们不妨一起来分析一个简单的例子,看看前面所讲到的 Mplus 程序指令是如何应用于实际分析的。

研究及模型简述:我们以 Wagner 和 Benoit 于 2015年在 Industrial Marketing Management 发表的文章为例。 文中作者研究了八个潜变量之间的关系,每个潜变


<a id="pdf-page-495"></a>
<!-- PDF页 495 -->

与管理研究的实证方法 (第三版)

量以三个观察变量来测量,样本数目是 527。 我们模拟了他们的研究数据作为例子。

Mplus 程序分析和解释:在图15 -6 中,我们可以清楚地看到,在标题句后, DATA 指令开始了真正的指令程序。Mplus 每一行的指令都是以分号 (;) 为完结,而感叹号 (1) 以后的只是评论,并不是真正的指令。

TITLE; Simulated Wagner & Benoit (2015) Industrial Marketing Management,44,166—179; DATA; FILE = EXAMPLEL. DAT; VARIABLE; NAMES ARE XI — X24;

MODEL; BE BY XI -X3;! Brand equity MS BY X4-X6; | Merchandising support MM BY X7-X9;! Margin maintenance ST BY X10-X12; —! Special treatment CA BY X13-X15; | Customer advocacy RV BY X16 - X18;! Relationship value BGI BY X19-X21; | Business growth intention RMI BY X22 - X24; | Relationship maintenance intention

OUTPUT; STDYX;! Request standardized coefficients 15-6 Mplus 程序例子

(1)DATA:FILE = EXAMPLE1. DAT DATA 是输入数据指令,指出了数据输入文件为 EXAMPLE1. DAT, (2) VARIABLE; NAMES ARE X1—X24 VARIABLE 指令指出了数据输入文件中变量的名称为 X1 至 X24。(3) MODEL; BE BY Xl—X3;! Brand equity MS BY X4—X6;! Merchandising support MM BY X7—X9;! Margin maintenance ST BY X10—X12;! Special treatment CA BY X13—X15; | Customer advocacy RV BY X16—X18;! Relationship value BGI BY X19—X21;! Business growth intention RMI BY X22—X24;! Relationship maintenance intention MODEL 指令指出了各个潜变量是以哪些观察变量来测量的。(4) OUTPUT; STDYX;! Request standardized coefficients OUTPUT 指令除了要求基本结果,还要求了各个估算值的标准值。建立结构方程模型的第四步和第五步是 Mplus 程序分析结果输出及解释。 通过输入的 Mplus 程序运行之后,我们会得到一大串对待测模型的输出结果。 如何


<a id="pdf-page-496"></a>
<!-- PDF页 496 -->

进行有效合理的分析呢?通常,我们会从以下四大方面着手:第一,分析参数估计的可行性。 结构方程模型本质上是个反复迭代 (iterative)测量的过程, 即在中间环节通过不断改变各个参数的估计,从而尽可能使得 A, 即

5 与 >,之间的差异最小。 在改变参数大小时,有可能会出现不合理值:例如,X观察变量间协方差和因子间协方差都应分别大于零,如果任意一方有小于零的数值, 即不合理的数值出现, 则即可全盘否定此结构模型。

第二,分析假设模型与实验数据的拟合程度。 我们会选择不同的拟合指数进行衡量,一般包括 chi-square.RMSEA.CFI 和 standardized RMR。 稍后会逐一介绍。

第三,参数估计是否显著。 在输出的结果中,除了每个参数的估计值,还有标准误差和 +t 值的估计。 如果选取第一类错误 (type I error) 值等于 0.05,那么我们要求合理 t 值应大于 1.96,

第四,X 的复相关系数 (multiple correlations)。 在结构方程模型中,每个观察变HEX 都有一个复相关系数,就像回归方程中的 R-square 一样, 我们同样希望这个复相关系数越大越好,因为如果它变小的话, 则说明观察变量与潜变量之间的关系也相应变弱了。

下面我们一起来观察上文例子中的 Mplus 输出结果,如图15 -7 所示, 看看有何新的发现。 首先判断其中并无不合理参数出现, 然后检查在因子负荷表中 (BY 指令) 每个参数所对应的四个数值分别是参数估计值标准误差; 值和显著性几率。 其中,所有显著性几率值都是小于 0.05 的,这说明因子负荷相关系数都是显著的。

MODEL FIT INFORMATION

Number of Free Parameters 100 Loglikelihood HO Value — 19830. 716 H1 Value — 19659. 688 Information Criteria Akaike (AIC) 39861. 432 Bayesian (BIC) 40288. 152 Sample-Size Adjusted BIC 39970. 726

(n® =(n + 2) /24) Chi-Square Test of Model Fit

Value 342. 056 Degrees of Freedom 224 P - Value 0. 0000 RMSEA (Root Mean Square Error Of Approximation) Estimate 0. 032 90 Percent C. L. 0.025 0.038 Probability RMSEA < =.05 1.000

图15-7 Moplus 输出结果

![原书图示（PDF第496页）](../images/fig-p0496-1.jpg)


<a id="pdf-page-497"></a>
<!-- PDF页 497 -->

478

CFI/TLI CFI 0. 980 TLI 0. 975 Chi-Square Test of Model Fit for the Baseline Model Value 6135. 950 Degrees of Freedom 276 P-Value 0. 0000 SRMR (Standardized Root Mean Square Residual) Value 0. 038

STANDARDIZED MODEL RESULTS STDYX Standardization

Estimate S.E. Est. /S. E.

BE BY

Xl 0. 685 0. 028 24. 253

X2 0. 765 0. 028 26. 957

x3 0. 861 0. 025 34. 242 MS BY

x4 0. 922 0. 054 17. 152

XS 0. 560 0. 044 12. 735

X6 0. 444 0. 044 10. 130 MM BY

X7 0.710 0. 036 19. 983

X8 0. 876 0. 036 24. 195

x9 0. 482 0. 039 12. 341 ST BY

X10 0. 667 0. 034 19. 823

X11 0.759 0. 033 23. 322

X12 0.722 0. 033 21. 850 CA BY

X13 0. 831 0.017 48. 148

X14 0. 836 0.017 49.131

X15 0. 905 0.014 64. 871 RV BY

X16 0.927 0.011 85. 809

X17 0. 846 0.015 56.517

X18 0. 888 0.013 70. 732 BGI BY

X19 0. 884 0.013 70. 275

X20 0. 905 0.012 78. 318

X21 0. 890 0.012 72. 537 RMI BY

X22 0. 736 0. 026 27.795

X23 0.915 0.022 40. 836

X24 0. 700 0. 028 25. 187 MS WITH

BE 0. 032 0.051 0.615 MM WITH

BE - 0.058 0. 052 - 1.100

MS -0.119 0.051 -2.319 ST WITH

BE 0. 135 0. 054 2. 508

MS 0. 046 0. 055 0. 844

MM 0. 158 0. 054 2.911

15-7 Mplus 输出结果 (续)

Two-Tailed P-Value

0. 0. 0.

So

0.

0. 0.

000 000 000

000 000

. 000

. 000. 000

000

000 000 000

000 000 000

. 000. 000. 000

000 000

. 000

. 000. 000. 000

538

### 0.271 0.020

0. 004


<a id="pdf-page-498"></a>
<!-- PDF页 498 -->

RISE ”结构方程模型

CA WITH BE 0.211 0.049 4.300 0.000 MS 0. 101 0.049 2.066 0.039 MM 0. 158 0.050 3. 135 0. 002 ST 0. 189 0. 051 3.691 0. 000 RV WITH BE 0. 199 0. 053 3. 760 0. 000 MS 0. 049 0. 049 0.997 0. 319 MM 0. 159 0.049 3. 234 0. 001 ST 0. 157 0.051 3. 080 0. 002 CA 0. 395 0. 041 9. 648 0. 000 BGI WITH BE 0. 426 0. 043 9.956 0. 000 MS 0. 042 0. 049 0. 868 0. 385 MM 0. 093 0.050 1. 875 0. 061 ST 0. 052 0. 052 0. 995 0. 320 CA 0. 258 0. 045 5.737 0. 000 RV 0. 396 0. 040 9.799 0. 000 RMI WITH BE 0. 046 0.051 0. 888 0. 375 MS 0. 231 0. 050 4. 638 0. 000 MM 0. 210 0.051 4.078 0. 000 ST 0. 108 0.053 2.051 0. 040 CA 0. 150 0. 048 3: 113 0. 002 RV 0. 092 0. 048 1.912 0. 056 BGI 0. 043 0. 048 0. 890 0. 374 Intercepts Xl 4.493 0. 145 30. 967 0. 000 x2 4. 693 0.151 31. 084 0. 000 x3 4, 553 0. 147 31. 004 0. 000 x4 2. 083 0. 078 26. 860 0. 000 xs 1.631 0. 066 24. 531 0. 000 X6 1.812 0.071 25.591 0. 000 X7 2.113 0. 078 26. 982 0. 000 X8 2. 483 0. 088 28. 210 0. 000 x9 3.207 0. 108 29. 706 0. 000 X10 2.171 0. 080 27. 204 0. 000 X11 2.237 0. 082 27.440 0. 000 X12 2. 222 0. 081 27. 387 0. 000 X13 4.442 0. 144 30. 935 0. 000 X14 5.020 0. 161 31.249 0. 000 X15 4.299 0.139 30. 840 0. 000 X16 3. 302 0.111 29. 843 0. 000 X17 3.274 0.110 29. 803 0. 000 X18 3. 142 0. 106 29. 604 0. 000 X19 3. 243 0. 109 29.759 0. 000 X20 3. 205 0. 108 29.702 0. 000 X21 2. 909 0. 100 29. 198 0. 000 X22 6. 582 0. 207 31.741 0. 000 X23 5.199 0. 166 31.327 0. 000 X24 3. 658 0.121 30. 281 0. 000

15-7 Mplus 输出结果 (续)


<a id="pdf-page-499"></a>
<!-- PDF页 499 -->

### 15.8 RAB

在结构方程中, 当我们谈到拟合度时,其实是指如何尝试改变各参数值的大小,从而使得拟合协方差矩阵更接近样本协方差矩阵, 即 A,, 更小。 一般地,我们会采用拟合函数 (fit function) F 来衡量 A., 的大小。 该值越小,说明两个矩阵之间的拟合程度越好。 根据估计的方式不同, 我们一般用的方法是最大概度 (maximum likelihood,ML),其拟合函数的最小值的计算公式为: fu = log D1 + tr SF") = log iS 1 =p +

(x apf yor x” aay?) (15-8)而整体拟合的最基本测量指标就是 Xx”,其公式为: x =(N-1)F (15 -9)

其中,N 为样本大小,F 为拟合函数的最小值。

伴随卡方一起的,我们还要同时考虑自由度和 p-value 的大小。 在众多不同的拟合指数中,x 是其中少数有已知分布情况的。 另外,还有拟合指数 root mean square error of approximation(RMSEA)。 由于分布情况已知,我们可以检测 x, 即A. 是否显著。 相对于每一个 Xx? 及其自由度 (DF) 值,我们可以找到显著的 p-value. XX 越小,p-value 越大, 则说明拟合协方差矩阵与样本协方差矩阵的差距越不显著, 最初假设的模型不会被推翻;反之,Xx 越大,p-value 越小, 则说明拟合协方差和矩阵与样本协方差矩阵的差距越显著,这时,我们最初假设的模型就要被推翻了。

然而,许多学者都特别注意到了一点, 即 x 的值对样本数量相当敏感。 样本越大,x 值也就越容易变得显著,从而使假设模型越容易遭到拒绝。 其实,我们从公式中也可以发现 x 值是非常依赖样本大小的,因为计算时是用样本数乘以 F 值。通常在结构方程实验中我们都需要大的样本数量,那么这时就会导致即使拟合协方差矩阵与样本协方差矩阵的差距不显著,也会使模型被拒绝的情况出现。 这个矛盾也就合理解释了为什么学者们都在不断找寻更合适的拟合指数。 现在,一般的软件都会同时支持超过 30 个的拟合指数。 下面,我们再简单向大家介绍儿个经常应用的拟合指数:

一个是 root mean square error of approximation(RMSEA)。

Estim: 5 = /—_xX = stimated RMSEA (N-1)(DF-1) (15 - 10)


<a id="pdf-page-500"></a>
<!-- PDF页 500 -->

RISK ”结构方程模型

这个概念最早是由 Steiger 和 Lind(1980) 提出的,然而是由 Browne 和 Cudeck (1993) 给它命名的。 当 RMSEA 等于或小于 0.05 时,代表假设模型拟合程度好;介于 0.05 到 0.08 之间时,代表拟合程度可以接受; 介于 0.08 到 0.10 之间时,代表拟合程度不高; 当超过 0.1 时, 则代表了模型与数据拟合程度很差。 总体来讲, RMSEA 越小,代表拟合程度越高。 除此之外,还提供了 Probability RMSEA <0.05的判断标准, 即用 p-value 测定这个假设。 当 p-value 大时,说明不显著, 则不拒绝假设模型; 当 p-value 小时,说明显著, 则要拒绝假设的模型。

男一个经常使用的拟合指数是 comparative fit index (CFI), 它的特征是比较底#8 (baseline) #1 A y° 和假设理论仑模型的 x (Bentler,1990), max (x — DF,0) max(y, - DF,,0)

CFI 公式中 x 指底线模型中的 x ”, DE, 指底线模型中的自由度。 这里所谈到的底线模型是只包含观察变量和误差项,忽略了潜变量和因子负荷间所有关系的一种模型。CFI 得到的值越大,代表拟合程度越好。 一般的规律是: 取值大于 0.9, 着大于 0.95, 则代表假设理论模型与数据的拟合度非常好。

还有一个经常使用的拟合指数是 standardized root mean square residual (SRMR),是拟合标准残差方差的平均值的平方根, 即一种平均标准残差方差。

-EY 3 > (s、° - oi?)}/ Eee (15 - 12)

SRMR 是标准值,因此不会受到 a 响, 一般的规律是:SRMR 取值小于O. 1 时为拟合度较好的模型。

男外,一些过去常用的拟合指数,诸如 relative chi-square, goodness of fit index (GFI) 和 adjusted goodness of fit index(AGFI),因为不少模拟研究发现它们的特性都有缺陷, 像对样本大小的依赖度高等,所以已经很少再被使用。

我们现在回到先前的模拟例子中来看看拟合度的结果。 如图15 -7 所示, 自由度(degrees of freedom) =224,minimum fit function chi-square =342. 056(p =0. 0000), RMSEA =0. 032, probability RMSEA <0. 05 =1. 000, CFI =0. 980, SRMR =0.038。 其中BYR? 的 p-value <0. 05 {HE probability RMSEA <0. 05, 1¢ 0.05 AK, 且其他的指标也显示了高的拟合度, 所以经过综合判断,我们认为此例假设的模型与样本数据拟合。

CFI=1- (15 - 11)


<a id="pdf-page-501"></a>
<!-- PDF页 501 -->

### 15.9 ”结构方程模型发展的新趋势

第一个大的新方向是以测量模型进行验证性因子分析, 通过检测来判断各个潜变量的信度和效度。 传统的检测信度方法是以克朗巴哈系数 (Cronbach's alpha)是否大于 0.7 来进行,但克朗巴哈系数假设了所有的观察变量与潜变量之间的因子负荷都是相同的,这在实证研究中并不多见。Fornell 和 Larcker(1981) 提出了在运用结构方程模型时,应该以没有假设因子负荷相同的变量信度系数 (construct reliability, CR) 来判断各个潜变量的信度。 计算变量信度系数的程序公式为: (20.14)

CR =: — (15 - 13) (Dia) + (Lie)

MALS -7 的 Mplus 输出结果中我们可以计算供应商的品牌资产 (vendor's brand equity) 的 CR:CR = (0. 685 +0.765 +0. 861)°/[ (0.685 + 0.765 +0. 861)? + (0. 531 +0.414 +0. 258) ] =0.816。 由于变量信度系数大于 0.7, 结论为供应商之品牌资产有足够的信度。

Fornell 和 Larcker (1981) 也提出了以观察变量的平均方差提取值 (average variance extracted) 大于 0.5 来检测收敛效度, 即潜变量解释了观察变量一半以上的方差。 从图15 -7 的 Mplus 输出中最后部分的 R-square 结果,我们可以计算供应商的品牌资产的平均方差提取值: AVE = (0. 469 +0.586 +0.742)/3 =0.599。 由于平均方差提取值大于 0.5,结论为供应商的品牌资产有足够的收敛效度。 但以平均方差提取值来检测收敛效度的一个缺点是可以有一个或一个以上的观察变量与潜变量间的关系并不密切,因此我们也应检测是否所有的因子负荷值都大于0.5(Hair et al.,2009)。

最后, Fornell 和 Larcker (1981) 提出了两个潜变量之间的判别效度应以两个平均方差提取值是否大于两者相关系数的平方来检定, 即一个潜变量对其观察变量的方差的解释度, 比对另一个潜变量的解释度高。 从图15 -7 的 Mplus 输出中最后部分的 R-square 结果,我们可以计算关系价值 (relationship value) 的平均方差提取值为:AVE = (0. 860 +0.716 +0.789)/3 =0.788。 供应商的品牌资产与关系价值之相关系数为 0.199,其平方为 0.0396。 由于供应商的品牌资产的 AVE 和关系价值的 AVE 都大于 0.0396, 结论为供应商的品牌资产与关系价值具有判别效度。


<a id="pdf-page-502"></a>
<!-- PDF页 502 -->

RAISE ”结构方程模型

第二个大的新方向是测量等同 (measurement equivalence/invariance, ME/ |) 概念的拓展与延伸。 过去要进行跨组 (cross group) 比较研究,例如比较潜变量的均值或潜变量之间的关系在各组别之间是否存有差异时,一般是以数条问卷题目答案的平均值作为潜变量的数值,之后以变异数分析或回归方程来计算跨组差别。这种方法最大的缺点是假设观察变量与潜变量之间的关系在各组别之间没有差异。 但实际上,特别是在跨文化的研究中,观察变量与潜变量之间的关系时有不同,因此需要进行测量等同检测来比较结构方程模型中的各个参数值是否存在器组差异,以确定比较潜变量的均值或潜变量之间的关系在各组别之间的差异并不是由测量差异而来。 进行跨组比较研究时,最基本的要求是结构不变性 (configural invariance), 亦即测量模型中潜变量与观察变量之间的形态在各个组别中相同。 当研究的目的是比较潜变量之间的关系在各组别之间的差异,例如在分析调节效应(moderating effect) 时,假如调节变量是一个类别变量 (categorical variable), 便可通过多组分析 (multi-group analysis) 来验证潜变量之间的关系在各组别之间是否相同, 这时便需要先确定量尺不变性 (metric invariance), 亦即因子负荷在各个组别中相同。 当研究的目的是比较潜变量的均值时, 则需要同时先确定量尺不变性和题项截距量尺不变性 (scalar invariance), 亦即因子负荷和题项截距量尺在各个组别中均相同 (Cheung & Rensvold,2000)。

特别值得我们关注的是测量等同在实际操作中的以下具体应用:

(1) 将结构方程模型在不同文化组别之间进行比较,可对跨文化的研究工作大有神益。

(2) 在教育学领域,结构方程模型有助于比较拥有不同水平学术成就或不同主修范围的研究对象之间的异同。

(3) 跨性别研究,因为男性和女性对某些问题的看法会有所差异,如对 “大减价 " 这个事件所体现出的分歧。

(4) 在心理学试验研究中,结构方程可帮助测量实验组和对照组对同一份调查问卷题目的不同看法。

(5) 在 360 度绩效评估中,研究表明,工作持有者与上司对其本人的工作表现评价会有所出入,从而导致一系列问题的产生。 经验证明,结构方程模型在以上这些研究分析方面,都有它擅长的一面。

传统的测量等同分析是以不受限模型 (unconstrained model) 的 x? 值与限制了因子负荷 (或同时限制了题项截距量尺) 在各组别中相同的受限模型 (constrained model) 的 x 值做比较。 假如两个模型的 x* 值差是显著的,测量等同便会被推翻。


<a id="pdf-page-503"></a>
<!-- PDF页 503 -->

由于 x 值差会受到样本数目的影响,Cheung 和 Rensvold(2002) 提出了将不受限模型和受限模型的 CFI 值进行比较,假如两者之差小于 0.01, 测量等同便得到证明。Mplus 提供了进行测量等同分析的简单而容易的方法,只要在 MODEL 指令后加上以下的分析指令便可:

ANALYSIS: MODEL = CONFIGURAL METRIC SCALAR

这些方法的不足之处是只能得到奥合指数的差异,但却没有计算因子负荷或题项截距量尺的跨组差异。 近年,Cheung 和 Lau(2012) 提出了直接估算因子负荷和题项截距量尺在不同组之间的差异,并以自助法 (bootstrap method) 来推算各差异的标准误差来分析统计显著性。 测量等同的详细狗述可参考 Vandenberg 和Lance(2000),多层构念的测量等同检测可以用高阶因子分析进行,详细拖述可参考 Cheung(2008)。

第三个大的新方向是潜增长模型 (latent growth model) 的发展。 有许多研究是观察研究对象随着时间轴的变化程度,如和人们的认知和态度的发展及变化。 举例来讲, 一个员工在步人职场之前对未来的工作会抱有一定期望; 步人职场两个星期之后, 当他有了一些初步认识之后,期望也会变得实际些, 同时对公司的观念也会有所改变;六个月之后,他的改变应该逐渐趋于稳定。 所以我们说一个人对一家机构的认知和观念会随着时间的流逝而发生变化。 同样,许多相似的概念和理论都是关于发展的,如上司与下属的关系、 培训的效果等。 潜增长模型以高阶 (higher-order) 结构方程模型来推算构念的增长模式,更重要的是可以检测特定变量对增长模式的影响。 潜增长模型的详细投述可参考 Chan(1998)。

第四个大的新方向是多层次模型 (multilevel model) 的进展。 多层次模型与高阶因子模型的最大差异在于高阶因子模型用以检测非独立的构念,而多层次模型则用以检测非独立的样本。 如图15 -8 所示的一个多层次数据的例子, 它包括四个样本 (subject),每个样本由三个题目 (item) 来测量,这四个样本又同时属于一个大组别 (group)。 例如,在人力资源管理的研究中,我们经常从员工中搜集数据,有些员工属于同一工作单位,或有共同的上司, 所以这些样本之间是相关的。 这个例子充分说明了有时我们搜集来的数据之间不是互相独立的,虽然分为四个样本,但其实互相之间都存在着一定关系。 那么,这种情况在分析时也需要特别处理。假如研究者的目的并不是分析不同层次变量之间的关系,而只是想去除数据的非独立性,那么 Mplus 提供了简单而容易的方法去处理样本误差的非独立性,只要在VARIABLE 指令加上组别变量的名称:

VARIABLE: CLUSTER = GroupID


<a id="pdf-page-504"></a>
<!-- PDF页 504 -->

并加上分析指令便可: ANALYSIS: TYPE = COMPLEX

Groupi

I I I I 1

Subject | Subject 2 Subject 3 Subject 4

x X x;

H15-8 多层次数据

近年很多研究都涉及不同层次的变量,如小组上司的领导方法会影响小组内各员工的个性与工作表现的关系。 早年的多层次分析以回归分析的等级线性模型(hierarchical linear modeling) 为基础,详细叙述可参考 Hofmann (1997) 与 Klein 和Kozlowski (2000)。 近年以结构方程模型来分析多层次理论有很大的发展,我们可将观察得来的变量之间的协方差矩阵分拆成为两个水平研究, 即变量组间协方差5 [4 (between-group covariance matrix) 和变量组内协方差矩阵 (within-group covariance matrix), oe 进一步可比较这两个水平之间的异同。 以结构方程模型来分析多层次理论的优点是能在推算变量组间协方差和矩阵时, pees 次变量的测量误差,因此可以更准确地推算高层次变量之间的关系。Mplus 也提供了简单而容易的方法进行多层次模型分析,Preacher 等 (2010)提供了很好的基本叙述。

第五个大的新方向是以结构方程模型做中介效应 (mediating effect) 分析的发展。 过去的中介效应分析是以 Baron 和 Kenny(1981) 为基础,检测自变量到中介变量的参数估值是否显著,以及中介变量到因变量的参数估值是否显著。 尽管所有的结构方程模型都能计算出中介效应值的标准误差,MacKinnon 等 (2002.2004) 在回归分析的基础上,指出中介效应非常态分布,因此一般的标准误差并不适用,他们建议以自助法来推算中介效应值的置信区间 (confidence interval),并以此估计参数是否显著。Cheung fil Lau(2008) 4 MacKinnon 等 (2004) 建议的方法应用于结构方程模型上,演示了怎样以自助法来推算潜变量间中介效应的置信区间, 从而检测中介效应的统计显著性。 最近 Lau 和 Cheung(2012) 更将他们建议的方法推广到估算特定的中介效应值和比较两个特定中介效应值的差异上面。

第六个大的新方向是以结构方程模型做交互作用 (interaction effect) 分析的发展,其中以交互作用来分析调节效应 (moderating effect) 最为重要。 当以回归分


<a id="pdf-page-505"></a>
<!-- PDF页 505 -->

析来检测调节效应时,可以两个观察变量值的积 (product term) 作为回归方程上的一个自变量, 并以此估计参数来检测调节效应是否显著。 但以结构方程模型来检测调节效应时, 潜变量值的积并不容易计算出来,最初 Hayduk (1989) 以多个方程来界定潜变量值的积, 其后又有不少学者提出各种方法来简化 Hayduk 的方程, Cortina 等 (2001) 对这些方法提供了很好的摘要总结和比较。 但这些方法不是非常复杂,就是推算存在问题。 直到近年, Mplus 提供了简单而容易的方法来建立潜变量值的积, 这一问题才得以解决,其方法是基于 Klein 和 Moosbrugger(2000) 的潜变量调节效应结构方程 (latent moderated structural equations,LMS) 来进行,当中没有估计两个潜变量值的积, 而是通过和矩阵 (matrix) 的运算来估计潜变量值的积对其他变量的影响。 图15 -9 展示了一个用以分析调节效应的 Mplus 程序,当中有三个潜变量 X、Y 和 2Z, 每个潜变量由四个观察变量来测量。X 是自变量,Y 是因变量, Z 是调节变量, 即 X 对了的效果受到 Z 值所影响。LMS 是以数字积分 (numerical integration) 来进行的,因此需要在 Mplus 程序中加入以下的分析指令: ANALYSIS:TYPE = RANDOM ALGORITHM = INTEGRATION在 Model 指令中,可以下面的指令来建立 X 和 2 的潜变量积 XZ: XZ | XXWITH Z最后,在 Model 指令中,加入以下的指令来估计 XZ 和 XZ 对 Y 的影响: YONXZXZ

要注意的是 LMS 分析的结果并不提供一般的契合指数,因此需要先运算没有潜

变量积的结构方程模型,得到了满意的契合指数后再加入潜变量积。

TITLE; LMS Model;each latent variable with 4 items DATA; FILE IS BASE. TXT; VARIABLE; NAMES ARE x1 — x4 zl — 24 yl —y4; ANALYSIS; TYPE = RANDOM; ALGORITHM = INTEGRATION;

MODEL; X BY xl ~x4;

Z BY zl -74;

Y BY yl -y4;

XZ | X XWITH Z;

Y ON X Z XZ;

15-9 用以分析调节效应的 Mplus 程序例子

最近学者所提出被调节的中介效应 (moderated mediation) 和被中介的调节效应 (mediated moderation),Cheung 和 Lau(2017) 演示了怎样以结构方程模型的 LMS

![原书图示（PDF第505页）](../images/fig-p0505-1.jpg)


<a id="pdf-page-506"></a>
<!-- PDF页 506 -->

方法来分析被调节的中介效应,并对所需 Mplus 程序做出了详细解释,其具体在实证研究中的应用可参考 Wayne 等 (2017) 的文章。Cheung 和 Lau(2017) 也展示并说明了以回归分析来推算被调节的中介效应值及其置信区间均存有很大的误差。对这题目有兴趣的读者可参考本书的第2章和 2017年 10月期的 Organizational Research Methods,当中有和多篇论文谈到以结构方程模型来检测被调节的中介效应。

综上所述,虽然近年来结构方程的应用日益广泛, 但是人们对其本质概念仍存在某些误解。 其实简单来讲,结构方程是基于假设模型,将拟合协方差矩阵与观察协方差矩阵相比较, 当二者差距缩小时, 则说明假设模型与原始数据接近。 所以,我们认为,只有清楚并深刻了解结构方程的内涵, 才能使其成为帮助我们进一步探索的更得力的助手和工具。


<a id="pdf-page-507"></a>
<!-- PDF页 507 -->

### 参考文献

Arbuckle, J. L. & Wothke, W. (1999). AMOS 4.0 User's Guide. Chicago; Smallwaters.

Baron, R. M. & Kenny, D. A. (1986). The moderatormediator variable distinction in social psychological research; Conceptual, strategic, and statistical considerations. Journal of Personality and Social Psychology, 51, 1173—1182,

Bollen, K. A. (1989). Structural Equations with Latent Variables. New York: John Wiley & Sons.

Browne, M. W. & Cudeck, R. (1993). Alternative ways of assessing model fit. In Bollen, K. A. & Long, J. S.

), Testing Structural Equation Models. Beverly Hills, CA; Sage.

Chan, D. (1998). The conceptualization and analysis of change over time; An integrative approach incorporating longitudinal mean and covariance structures analysis (LMACS) and multiple indicator latent growth modeling (MLGM). Organizational Research Methods, 1,421—483.

Cheung, G. W. (1999). Multifaceted conceptions of selfother ratings disagreement. Personnel Psychology, 52, 1—36.

Cheung, G. W. (2008). Testing equivalence in the structure, means, and variances of higher-order constructs with structural equation modeling. Organizational Research Methods, 11,593—613.

Cheung, G. W. & Lau, R. S. (2008). Testing mediation and suppression effects of latent variables. Organizational Research Methods, 11,296—325.

Cheung, G. W. & Lau, R. S. (2012). A direct comparison approach for testing measurement invariance. Organizational Research Methods, 15,167—198.

Cheung, G. W. & Lau, R. S. (2017). Accuracy of param-

eler estimates and confidence intervals in moderated

488

mediation models; A comparison of regression and latent’ moderated structural equations. Organizational Research Methods, 20(4),746—769.

Cheung, G.W. & Rensvold, R. B. (1999). Testing factorial invariance across groups; A reconceptualization and proposed new method. Journal of Management, 25,1— 27.

Cheung, G. W. & Rensvold, R. B. (2000). Assessing Extreme and Acquiescence Response Sets in Cross-Cultural Research Using Structural Equations Modeling. Journal of Cross-Cultural Psychology, 31 (2),187— 212.

Cheung, G. W. & Rensvold, R. B. (2001). The effects of model parsimony and sampling error on the fit of structural equation models. Organizational Research Methods, 4,235—263.

Cortina, J. M., Chen, G. & Dunlap, W. P. (2001). Testing interaction effects in LISREL; Examination and illustration of available procedures. Organizational Research Methods, 4,324—360.

Fornell, C. & Larcker, D. F. (1981). Evaluating structural equations models with unobservable variables and measurement error. Journal of Marketing Research, 18, 39—S0.

Hair, J. F., Black, W. C., Babin, B. J. & Anderson, R. E. (2009). Multivariate data analysis (7th Ed.). Upper Saddle River, NJ; Prentice Hall.

Hayduk, L.A. (1987). Structural equation modeling with LISREL; Essentials and advances. Maryland; Johns Hopkins University Press.

Hofmann, D. A. (1997). An overview of the logic and rationale of hierarchical linear models. Journal of Management, 23,723—744.

Joreskog, K. G. & Sérbom, D. (1996). LISREL8: User's


<a id="pdf-page-508"></a>
<!-- PDF页 508 -->

Reference Guide. Chicago: Scientific Software International, Inc.

Klein, K. J. & Kozlowski, S. W. J. (2000). Multilevel Theory, Research, and Methods in Organizations; Foundations, Extensions, and New Directions. San Francisco; Jossey-Bass.

Klein, A. & Moosbrugger, H. (2000). Maximum likelihood estimation of latent interaction effects with the LMS method. Psychometrika, 65,457—474.

Lau, R. S. & Cheung, G. W. (2012). Estimating and

comparing specific mediation effects in complex latent

variable models. Organizational Research Methods, 15,3—16.

MacKinnon, D. P., Lockwood, C. M. & Williams, J. (2004). Confidence limits for the indirect effect: Distribution of the product and resampling methods. Multivariate Behavioral Research, 39,99—128.

Preacher,K. J., Rucker, D. D. & Hayes, A. F. (2007). Addressing moderated mediation hypotheses; Theory, methods Research, 42,185—227.

and prescriptions. Multivariate Behavioral

RISK ”结构方程模型

Preacher, K. J., Zyphur, M. J. & Zhang, Z. (2010). A general multilevel SEM framework for assessing multilevel mediation. Psychological Methods, 15,209—233.

Steiger, J. H & Lind, J. M. (1980). Statistically-Based Tests for the Number of Factors. lowa City, 1A; Paper presented at the Psychometrika Society Meeting.

Vandenberg, R. J. & Lance, C. E. (2000). A review and synthesis of the measurement invariance literature; Suggestions, practices, and recommendations for organizational research. Organizational Research Methods, 3, 4—10.

Wagner & Benoit (2015). Creating value in retail buyervendor relationships; A service-centered model. Industrial Marketing Management, 44,166—179.

Wayne, S.J., Lemmon, G., Hoobler, J. M., Cheung, G. W. & Wilson, M.S. (2017). The ripple effect; A spillover model of the detrimental impact of work-family conflict en job success. Journal of Organizational Behavior, 38(6),876—894.

ARASH, ak ABB AA FW (2004). 结构方程模型及其应用.北京:教育科学出版社.


