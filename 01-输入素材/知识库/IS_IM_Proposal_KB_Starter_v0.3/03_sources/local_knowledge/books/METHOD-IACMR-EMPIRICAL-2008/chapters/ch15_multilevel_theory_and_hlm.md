---
resource_id: METHOD-IACMR-EMPIRICAL-2008
edition_year: 2008
chapter_id: ch15
title: 第十五章 多层次理论模型的建立及研究方法
pdf_page_start: 346
pdf_page_end: 371
source_line_start: 5980
source_line_end: 6557
tags:
- multilevel
- HLM
- aggregation
- centering
- cross_level
- sample_size
status: source_preserved_ocr_markdown
rights: user_supplied_private_research_copy
---

<a id="pdf-page-346"></a>
<!-- PDF页 346 -->

## 第十五章 多层次理论模型的建立及研究方法


<a id="pdf-page-347"></a>
<!-- PDF页 347 -->

引 BS组织是一个多层次的、层层相扣的系统结构。比如个人存在于团队之中,团队存在 '于部门之中,部门存在于公司之中,公司存在于产业之中,产业存在于一定的文化之中。 |个人、团队、公司、产业及文化特性在此多重的层次中相互影响与结合,以创造产出。因此,研究者必须视组织为一个整合的系统。然而,传统的组织研究已将组织切割成个 |人,群体与组织层次,研究者不是倾向下强调宏观(macro) 的观点就是微观(micro) 的观;点。微观的观点主要源自于心理学,着眼于个人与行为的差异;而宏观的观点主要源自!于社会学,强调个人行为的集体或共同的反应。一如组织研究学者多年来所注意到的,只采用宏观的观点或只采用微观的观点无法精确:全面地解释组织行为。宏观的观点不重视个人之间的差异,且忽略个人的人格、情感、行为及互动可能提升到更高层次的现象的过程;反之,微观的观点不重视个人 |所存在的情境,可能忽略此情境对个人差异效果的限制。 |在过去十年的组织研究中,多层次(multilevel) 的观点逐渐发展成熟,确认了组织既 |是宏观亦是微观的观点,而且在综合方法上应该考虑两种情形:一是群体、组织及其他情境因素如何由上而下(top-down) 影响个体层次(individual-level) 的结果变量,二是个人知觉态度及行为由下而上(bottom-up)以形成群体、次单位与组织的现象。至目前为止,许多组织学者对多层次整合方法的理论及方法论之发展已经有长足的贡献, Klein和 Kozlowski (2000)已相当完整地收录了多层次研究的现况。本章的目的是说明多层次理论的建立与统计方法上的一些重要元素,将从简要浏览多层次的研究开始,再进入单位层次(unit-level)构念与聚合议题(aggregation issues,亦译为合并议题)的介绍,接着使用一个真实的样本数据来介绍多层线性模型 (hierarchical linear modeling,HLM,亦译为阶层线性模型)的分析流程。一、多层次理论的建立、模型的类型与分析策略1.1 建立多层次理论的重要问题 | Kozlowski 和 Klein (2000)对于多层次组织理论的建立提供了很详尽的指导方针,并极力主张研究者去思考下列问题: | 1. 什么是多层次理论的建立与研究应该要重视的? 具体来说,什么是所欲研究的 |内生构念(endogenous construct)或因变量(dependent variable)? 因变量(而不是自变量)是用来驱动分析层次、选择自变量以及决定理论所欲解释的连结过程的。 | 2. 如何连结不同层次间的现象?理论必须解释较高层次的情境因素对较低层次的总二五总 | 多层次理论机型的建立及研究方法 | 333;


<a id="pdf-page-348"></a>
<!-- PDF页 348 -->

过程与结果的由上而下直接或调节的效果,或解释较低层次的构念如何由下而上形成 |较高层次的现象,又或者是两个皆解释。.

3. 由上而下与由下而上的过程是从哪里开始,又在哪里结束? 具体来说,什么才是模型中适当的构念分析层次?

4. 何时会发生由上而下与由下而上的过程? 何时效果会显现?

5. 为什么要或为什么不在模型中建立一些假设? 为什么这个模型要以多层次理论 |为基础? 为何有些变量间的关系是由下而上或是由上而下? 例如,为何模型中的安全氛围(safety climate)这个变量是群体层次的变量而不是个人层次的变量? 车视之为群体层次的变量,我们需要作出什么样的假设?

Kozlowski 和 Klein (2000)强调,一个仔细的多层次理论建立应该说明上述的问题,并且实现构念的理论层次测量、研究设计与数据分析之间的一致。1.2 多层次模型的类型

”接下来将简要地说明在多层次的研究中,已经被使用过的广泛的多层次模型。

1. 跨层次直接作用模型(cross-level direct-effect models) 检测在较低层次(如个人层次)的结果变量上,较高层次(如单位层次) 自变量(independent variables) 的主效果(main effects),或同时分析较高层次与较低层次的主效果, Klein, Dansereau 和 Hall (1994)称之为混合因子模型(mixed-determinants models)。例如,Siebert,Silver 和 Randolph (2004)发现,团队层次的授权氛围 (team-level empowerment climate)与员工层次的心理授权(employee-level psychological, empowerment) 相关,且心理授权中介于团队层,次的授权氛围与个人层次的工作满意度及工作绩效。图1 WH Siebert, Silver 和 Randolph的模型。

Hl 跨层次直接效果模型

资料来源:Siebert, Silver and Randolph (2004)。.

2. 跨层次调节模型(cross-level moderator models)检测两个较低层次构念之间的关系如何被较高层次的构念所调节,或是检测较高层次的构念与较低层次的结果变量之间的关系,如何被另一个较低层次的构念所调节。例如, Hofmann, Morgeson 和 Gerras

![原书图示（PDF第348页）](../images/fig-p0348-1.jpg)


<a id="pdf-page-349"></a>
<!-- PDF页 349 -->

(2003)检验了团队层次的安全气候(safety climate)对个人层次的领导者部属交换(leader-member exchange) 与员工的安全公民角色定义(safety citizenship role definitions) Z [A] '关系的调节效果,结果发现,当正面的安全气候存在时,领导者部属交换与安全公民角色定义之间的相关性更高。图2% Hofmann, Morgeson 和 Gerras 的模型。安全气候| |领导者部属安全公民人民生 |:交换 TT 人——一安全公民行为:图2 跨层次调节模型资料来源:Hofmann, D. A., Morgeson, F. P. and Gerras, S. J. (2003).. 3. 跨层次青蛙池塘模型(cross-level frog-pond models)说明较低层次的个人在较高:层次中的相对位置,对较低层次的结果变量有何影响。同样的一只青蛙,假若池塘很大,这只青蛙看起来可能会很小;若池塘很小,这只青蛙看起来就可能很大。 例如,假设我们要检测薪资的高低与工作满意度之间的关系,个人的工作满意度可能就会取决于其相对于和群体中同事的平均薪资水准。图3 为此模型的概念化。' Ki — Xeroup mean Yy, + | 图3 跨层次青蛙池塘模型' 4. 一致的多层次模型(homologous multilevel models)说明构念以及连结构念间的关系是可被概化到不同组织的实体上的。在这种模型中,两个或两个以上变量之间的关! | 系是可能同时存在于个人、群体及组织等多个层次中的。例如,DeShon,Kozlowski, | Schmidt, Milner #1 Wiechmann (2004)检验一个多重目标绩效模型在个人和团队层次上° 的一致性,结果发现79% HRRETA SAAB Re, EMT TE WAKA A: 时存在于不同层次的多层次模型。图4 DeShon, Kozlowski, Schmidt, Milner 和 Wiec- | H hmann 的模型。 1 1.3 ”多层次模型的分析策略 |关于方法论的发展,现已有许多可行的多层次分析技术,包括协方差分析(analysis | of covariance, ANCOVA, 亦译为共变数分析)、使用普通最小二彝回归 (ordinary least | squares regressions, OLS, 亦译为最小平方回归分析) 的情境分析 (contextual analysis) | (James and Williams, 2000)、组内与组间分析(WABA,, Dansereau, Alutto and Yammari-: no, 1984; 亦见 Dansereau and Yammarino, 2000)、使用 HLM 分析多层次随机系数模型! | (Bryk and Raudenbush, 1992) WR & Ue St AE aH #4 5} HF (multilevel covariance structure | | 第十五章 | 多层次理论模型的建立及研究方法 | 335 | t k

![原书图示（PDF第349页）](../images/fig-p0349-1.jpg)

![原书图示（PDF第349页）](../images/fig-p0349-2.jpg)


<a id="pdf-page-350"></a>
<!-- PDF页 350 -->

”团队自律过各 " | He |意向 2 [eee a H&s Hy" |绩效导向团队效能关注团队的努力 |反馈。个体 -一一-~一-一~------~-----~-- “团队、. “个体和团队、。 个体自律过程个体特征 BP 行动绩效导向自我效能关注自我的努力: 图4 一致的多层次模型 1资料来源:DeShon, Kozlowski, Schmidt, Milner and Wiechmann (2004), | analysis) (Muthen, 1994)。由于篇幅的限制,无法详细介绍所有类型的多层次模型与分析技术,因此,本章着重在数据合并(data aggregation) 议题与 HLM 的介绍,前者是将混合因子模型中较低层次构念的回答进行聚合的重要议题,后者是越来越多学者用来分析跨层次模型的方法。二、多层次分析的构念与单位层次构念的数据聚合 | Kozlowski 和 Klein (2000) 认为构念是多层次理论的组成要素,因此,建议研究者明 |确地说明假设理论模型中构念的所在层次。多层次模型常包含个体层次 (individual- 1; level)与单位层次(unit-level) 的构念,例如,个体的人格、认知、情感与行为是典型的个 t人层次的构念,而组织气候、组织文化与团队绩效是典型的单位层次的构念。然而,一 |个变量在某些理论模型中是个人层次的构念,但在其他模型中却有可能是单位层次的;构念,例如,正向情感(positive affect) 被认为是个人层次的构念,且与个人的乐观、被喜 |爱程度、社交能力、主动有活力等特质有关。George(1990)认为通过吸引一王选一留任的程序(ASA,Schneider, 1987)与群体社会化的程序,同一群体的成员可能会有相似的情感反应,因此,她以正向情感语调(positive affective tone)作为群体层次的构念,并将 j其定义为同一群体内一致的正向情感反应,且发现此构念与群体层次的旷工行为呈现 |负相关。所以,研究者必须明确地解释为何一个构念被放置在某层次的理论根据。个人层次的构念是以个人层次来衡量的,其操作比较直观简单。然而, 对单位层次构念的操作就比较复杂。学者们(如,Chan,1998; Kozlowski and Klein, 2000)对单位层次构念的类型有详尽的探讨,并说明他们在操作上的不同。这些学者提出单位层次构. 念的类型可分为:共享单位特性(shared unit properties)、总体单位特性(global unit prop- |

!

![原书图示（PDF第350页）](../images/fig-p0350-1.jpg)


<a id="pdf-page-351"></a>
<!-- PDF页 351 -->

erties) 以及形态单位特性(configural unit properties)。接下来我们将简单地儿述这三种类型的构念,并介绍证明聚合(由个人层次到单位特性)合理的统计方法。2.1 单位层次构念的类型

共享单位特性:此类型的构念源自于组织内单位成员的经验、态度、知觉、价值观、认知及行为等,且被假定在 ASA、社会化及其他心理历程的作用下,会体现为一个单位层次的构念。例如,组织气候就是组织成员共享组织内的惯例、、政策及程序等。所以,操作此构念的关键在于将相同单位内的个别成员之回答分数计算为单位平均数,以育合为单位层次,而聚合的方法需要理论与实证的支持。在理论上,研究者须说明单位内回答的一致度和一致性如何从个别层次的特征浮现而来;而在实证上,研究者需证明达到了聚合的统计前提,后续将会对聚合分析有详细的探讨。此外,为了操作共享的构念,研究者需要取得一个具有代表性的样本,以取得构念的相关信息。根据参考点的不同,共享单位特性还可分为两种类型:

直接一致构念(direct consensus constructs,亦译为直接共识构念):与共享单位特性一样,此构念源自于个别团体成员,并由聚合个别的分数而取得。此构念呈现出团体成员分享他们个别的知觉或特质,如认知能力、风格、人格、智力及行为变量 (Chan, 1998)。犹如曾提过的,George (1990)衡量工作团体的情感语调是将个别情感的测量聚合到团体层次,并检测团体内情感的一致性而产生了两个聚合后的变量:正向的团体情感语调及负向的团体情感语调,此构念描述的是团体属性(group attribute) 而非个别心理属性(individual psychological attribute),

移转参考点共识构念(referent-shift consensus constructs):与直接一致构念一致,此构念源自于个别团体成员,并由育合个别的分数而取得。然而,不同于直接一致构念的是,移转参考点共识构念只有在成员共享其团体属性的知觉时才有意义。这种构念的问项可能为“我有信心我的团队可以完成此项任务”。此构念描述的是团体集体的属性(group collective attribute) 而非团体属性或个别心理属性。Ehrhart (2004)将移转参考点共识模型应用于检测部门的程序公正氛围(procedural justice climate),要求员工去思考在工作部门中获得奖酬的程序,其间项包含“这些程序曾一贯地在你的部门中实行吗?”这个例子中的参考点为部门,用以了解团体的集体程序正义。

总体单位特性:此类型的构念相对而言是客观的、描述性的.易于观察到的单位特征。总体的构念不同于共享单位特性,它直接源自于单位层次,而非个人层次,例如,公司的年龄,规模大小位置、策略。总体的构念决定于单位的结构或功能,而非决定于个别成员的知觉、经验、态度等,而操作总体单位特性的关键在于尽可能地向主题专家

| (subject matter experts, SME) 取得精确的信息或档案数据,因为在评估总体单位的特性时,主题专家的丰富知识可能有助于降低测量误差,而主题专家之间的回答共识和一至性可由后续讨论的聚合验证统计方法处理。LEED | 多层次理论模型的建立及研究方法 | 337


<a id="pdf-page-352"></a>
<!-- PDF页 352 -->

形态单位特性:此类型的构念是指在单位中,个人特征的形态或配置情形。如同共享的构念,配置的构念也是源自于个人层次,然而,并不假设单位成员之间会趋于一致,例如,年龄多样化与性别多样化是两个形态单位的构念,且分别描述了单位成员的年龄与性别的分布,因此,成员间不必有相同的年龄或性别。理想上,研究者在操作形态构念时,必须向单位中的所有成员取得构念的信息(如年龄),车无法达到理想的回答率(response rate),研究者必须证明回答的样本具有足够的代表性。此外,研究者不必评估个别成员之间的一致性,因为形态构念的分数可由个别成员分数的最小值、最大值、方差(亦译为变异数) 或标准差等数值来计算。例如,Lindell 和 Brandt (2000) 以领导者、团队、角色及工作特性为特征来衡量组织气候,并使用组织气候的方差来推估气候的一致性,在此例子中,方差被视为是群体的一个概括的特征或是形态。,; 在上列的单位层次构念的类型中,对共享单位特性(不论是直接一致构念或移转参考点共识构念)与主题专家所评估的总体单位特性而言,聚合个人层次的回答是必需的。因此,以下将探讨常被用来评估是否可以聚合个人层次作为单位层次的统计验证方法。2.2 聚合的统计验证方法(justification statistics for aggregation)在聚合个人的回答到单位层次之前,研究者必须确认聚合有理论与实证的支持。而在实证的验证上,在文献中有一些讨论(如,George and James, 1993; Yammarino and Markham, 1992), Bliese (2000)在其著作中详细说明了有关珍合的许多一致度与信度指标,我们接下来将介绍三个在多层次研究中常用的指标,即组内一致度 (within-group agreement)、组内相关(1)或ICC(1) [intra class correlation (1) or ICC(1)]和组内相关(2)或ICC(2)[intra class correlation (2) or ICC(2)]。1. 组内一致度| 首先,研究者必须确认是否有高度的组内一致度。组内一致度是指回答者(如相同单位的个别成员)对构念有相同的反应程度 (Kozlowski and Hattrup, 1992)。如 Bliese (2000)所提到的,在组织文献中最常用来衡量组内一致度的有适用单一问项量表的Tog) 或适用多问项量表的 rs (James, Demaree and Wolf, 1984; 1993)。James 等(1984)对组内一致度的衡量是使用观察到的群体方差与期望的随机方差相比较。单一问项量表的公式如下: Taga) = 1 ~ (s/o8o) EBA ry) RRR P bMS SX 的组内一致度,s: 是指观察到的X方差,而 o纪是假设所有回答者只存在随机测量误差下所期望的X 方差。多问项量表的公式如下:: a J[1 = (sh) oi] |?J1- (s/o8)] + (s5/0%,) '


<a id="pdf-page-353"></a>
<!-- PDF页 353 -->

上述公式中,rs是指在了个平行的问项上所有回答者的组内一致度,5是指在 J个问项上所观察到的方差的平均数,而 os是指假设所有回答者只存在随机测量误差下所期望的方差。

以上的公式可用来计算每个群体的组内一致度。在组织文献中,基本法则是呈现众群体的 +,中位数或平均数,假若 rs值大于 0.70,表示京合有足够的一致度。有一些情况是,虽然 r,值大于0.70,但某些群体可能存在相当低的一致度,在此情形下,研究者可使用回归或 HLM 去分析在有或没有这些群体的情况下,结果是否会有很大的不同,车是,则必须进一步研究是否适合将高组内一致度与低组内一致度的样本结合在一起。然而,将低7,值的群体去除很可能会删除掉某些存在于群体中的现象。例如,当有子气候(subclimates)存在时,服务气候的 +。,值可能很低,但这不一定意味着完全没有一致度存在(Lindell and Brandt, 2000)。在此例子中,研究者可探究子群体间在个人层次或群体层次变量上的差异性,而不是将这些群体去除。

James 等(1984)提出了 o3,即期望随机方差(expected random variance) 的选择之一是假设群体成员的回答呈现统一性分布(uniform distribution)下所得到的方差。均勾分布是指群体成员的每一个回答选项都有相同的回答人数的分布状态,例如,假设有 10个人来回答一个五点量表(5-point scale) 的构念,分别有2 个人回答1、2 个人回答2、2个人回答3、2 个人回答4以及2个人回答5。在均匀分布下,osu = (C? -1)/12,C WE案选项的数目,在李克特量表(Likert scale) 中的五点量表、七点量表与九点量表的 0%分别为2、.4 与 6.67。

然而,均匀分布可能不是一个代表实际期望分布的选择,因为多数个人的回答都存 -在回答偏误。例如,在正向反应偏差(positive response bias) 情况下,回答者更可能会选择正面的选项(如3、4 或5),此种回答范围的限制将会降低组内方差(亦译为组内变异,相较于均匀分布的方差),造成群体成员之间有高度一致度的幻觉。James 等(1984)针对期望分布提出了一些限制与建议方案,例如,研究者可以使用偏态分布(skewed distribution) 的方差作为计算 r。,时的期望方差,至于选择正偏态(positive skew)或负偏态(negative skew),取决于所要衡量的变数。然而,Bliese (2000)提到因为有无限个偏态分布可选择,所以偏态程度的选择可能会较武断,这也是研究者要作的决定,而以回答偏误调整过的 r。,则提供了更谨慎的组内一致度的衡量方法。James 等提供了三个负偏态期望分布的选择,以模拟不同的偏态程度。例如,在小偏态的情形下,五点量表每个回答选项的几率可设定为:1 =0.05、2 =0.15、3 =0. 20.4 =0.35 和5 =0.25,在此例子中,osy =1.34,将其代入上述公式即可算出 7。。。

Kozlowski 和 Hults (1987)提出了另一个期望方差的选择。他们建议:首先,使用有独立数据点的数据库的分布方差来设定组内一致度的下限,再使用均匀分布的方差来设定组内一致度的上限,而真实的一致度会界于以上两者之间。

Bliese 等学者建议使用随机群体再抽样(random group resampling,RGR)来估计期

| SLER | 多层次理论模型的建立及研究方法 | 339


<a id="pdf-page-354"></a>
<!-- PDF页 354 -->

望随机分布(如 Bliese and Halverson, 1996; Bliese, Halverson and Rothberg, 1994)。RGR 是随机地分派个体到数个与真实群体一样大小的假性群体(pseudo group)中,假性群体方差的分布是期望分布,它的方差被用来与真实群体方差作比较,以确定真实群体方差是否显著地小于或大于假性群体方差,假若真实群体方差显著地小于假性群体方#,表示具有组内一致度。此外,Bliese (2000)建议使用平均假性群体方差作为计算 r。。时的期望随机方差,使用 RGR 计算一致度的 S-PLUS(Statistical Sciences, 1997)算法可咨询 Bliese。

2. 组内相关(1)或ICC(1)

除了验证个别的回答具有充分的组内一致度之外,研究者必须在到合个别回答到群体层次之前,先检测是否有足够的组间差异,组间方差(亦译为组间变异) 的存在是检测群体层次构念与其他构念之间关系的要索。例如,为了检测服务氛围(是由个别员工的回答算出平均数,以作为店层次的构念)与店销售量之间的关系,我们必须得知员工们对服务氛围的知觉,在店与店之间是否有显著的变异,假若店与店之间在服务氛围上没有差异(但在销售量上有差异),则服务氛围与销售量之间将有可能没有关系存在。

对于某一个变量在个人层次的回答,例如服务氛围,我们可通过 HLM 分析将其方差分为组间方差(between-group variance)与组内方差(within-group variance)。 服务气候在个人层次的回答的总方差为组间方差 +组内方差,如此,我们可由以下公式计算出服务氛围的ICC(1)或是店与店之间在服务氛围上的变异程度:

: ICC(1) = 组闻方差 /(组间方差 + 组内方差)

此外,HLM 亦使用卡方检验(chi-square test)来检测组间方差是否具有统计上的显著性,假若服务氛围的组间方差是显著的,且 ICC(1)是有意义的,那么我们便有另一个证据显示,将个别的回答聚合到店层次是可行的。James (1982) 回顾了组织研究,并发现ICC(1)的范围在0.00 到0.50 之间,中位数为 0.12,但 Bliese (2000)认为这个范围可能高估了,因为 James 将 eta-squared® 与 ICC(1)视为等同。当一个群体样本数很大时,eta-squared 等同于 ICC(1),然而,当群体样本数很小时,相较于 ICC(1), eta-squared显著地被高佑了。因此,在实务上.,研究者可以检测组间方差是否显著,但不一定要以0.12 作为是否可以聚合的判断值。

3. 组内相关(2)或ICC(2)

第二个要考虑的组内相关系数是 ICC(2)。ICC(2)是指群体平均数的信度(reliability) (如 Bartko, 1976),亦即将个人层次变量聚合成群体层次变量时,此变量的信度。ICC(2)也与ICC (1)和群体大小有关,其公式如下:

@ eta-squared(n”) =组间平方和/总平方和,它通过 ANOVA 的数值计算,用下检验来判断显著性,以检验组间是否有差异,即了解个别分数的变异有多少是来自于组间差异。然而,F 检验易受群体样本数的影响,当样本数较大时,eta-squared 易显著,反之,样本数过少时,则有高估的倾向。!


<a id="pdf-page-355"></a>
<!-- PDF页 355 -->

tee) = rt eery

上述公式中,k 表示群体样本数的大小。犹如 Bliese (2000)所提到的,ICC(1)、ICC(2)与群体样本数的大小这三者之间的关系如下:ICC(1)可以被视为是一个信度的测量值,而这个测量值和单一群体平均数有关(James, 1982),当 ICC(1)很大时,单一群体成员的回答可能就足以提供相对稳定的群体平均数,而当 ICC(1)很小时,群体平均数就必须以多个群体成员的回答来估计。Bliese (1998)指出,在检测群体层次构念与其他构念之间的关系时,有可信的群体平均数或高 ICC(2)是必要的。例如,Bliese 发现,当有高 ICC(2)时,即使因变量与自变量的1CC(1)为 0.01,即较低层次的回答只有1%来自于组间方差,依然能够在群体层次检测出因变量与自变量之间的关系。

要有高 ICC(2)就必须要有很大的群体样本数,犹如为了要有可信的量表,我们必须使用多个相同意思的问项来测量,因此,为了获得可信的群体平均数,必须取得更多样本数的回答。在 ICC(1)固定时,群体样本数越大,ICC(2)就越高。ICC(2)最好是要达到 0.70,但在组织研究中,尤其是小群体的研究中,通常无法有很大的群体样本数,因此,在多层次组织研究中,ICC(2)通常小于 0.70。针对此议题,有学者认为即使有相对低的ICC(2),但假若聚合获得理论支持且有高的 7,以及显著的组间方差 RAHA A行的(Chen and Bliese, 2002; Kozlowski and Hattrup, 1992);但车ICC(2)很低,研究者必须承认低群体平均数的信度可能已阻碍了聚合后变量效果的检测,而且相较于高 ICC (2),低ICC(2)所观察到的变量效果可能被低估了。

### 三、关于 HLM 的介绍

接下来,我们将介绍一个跨层次模型的统计分析程序,其中,结果变量(亦称因变量)是个人层次的变量,自变量则是个人层次和群体层次的变量丝有,而所使用的分析方法与软件为HLM。Bryk 和 Raudenbush (1992)中对 HLM 有很详尽的说明,Hofmann与他的同事亦对组织研究者使用 HLM 有清楚的介绍(Hofmann, 1997; Hofmann and Gavin, 1998; Hofmann, Griffin and Gavin, 2000),在此,我们仅作简要的讨论,强烈地建议有兴趣的读者参考上述学者的著作。

在使用 HLM 时,自变量可能是来自于较低层次的构念,例如个人层次(可称为 Level-1 变量);或是较高层次的构念,例如群体层次(可称为 Level-2 变量)。而这些变量之间的关系可由以下的模型求得:

Level-1 Model: Y, =Bo +B,X, + ry

Level-2 Model: By; = Yoo + Yo: G + Uo;

By = V0 t¥nG; + Ui,了;是指个人i在j群体中的结果变量,X,是个人i在j群体中的预测因子之值,B与BLE | 多层次理论模型的建立及研究方法 | 341


<a id="pdf-page-356"></a>
<!-- PDF页 356 -->

By则是每个;群体分别被估计出的截距项与斜率,rj为残差项。G, 是指群体层次的变量,yw与 Yio为 Level-2 RHA yo Fy, WE G6 与 Level-1 公式中的截距项与斜率项之斜率,U6与 Vj为 Level-2 的残差项。因此,在Level-1 Model 中,可检验出 Level-1 变量和Level-1 变量之间的关系,而在 Level-2 Model 中,可检验出 Level-2 变量和 Level-1 变量间的关系,以及 Level-2 变量如何干扰两个 Level-1 变量间的关系。3.1 HLM 的优点

许多学者提到,普通最小二乘回归法(OLS)忽略了同一个单位中阶层数据的相互

依赖性,因此,普通最小二乘回归可能会产生偏误与无效的估计标准误(standard errors)

(如 Bryk and Raudenbush, 1992; Hofmann, 1997),并且会增加第一类误差与第二类误差(Bliese and Hanges, 2004),所以,相较于普通最小二乘回归,HLM 在分析阶层性的数据上有许多优点。

第一, HLM 能够明确地分析赃套(nested) 性质的数据(比如, 个人嵌套于团队之中,团队嵌套于部门之中,部门嵌套于公司之中)。HLM 除了可以同时估计不同层次的因子对个人层次的结果变量有何影响之外,还能将这些预测因子保持在适当的分析层次(Bryk and Raudenbush, 1992)。此外, HLM 亦有助于多层次理论的发展(Kozlowski and Klein, 2000),因为在使用 HLM 时,研究者必须清楚地表明每一个构念的分析层次(例如要放在 Level-1 或 Level-2)与各层次构念间的关系为何(例如是在 Level-1.Level-2或跨层次的关系)。

第二,HLM 能够改善 Level-1 或个人层次效果的估计。如同 Bryk 和 Raudenbush (1992)与 Raudenbush,, Bryk, Cheong 和 Congdon (2004)所提到的,HLM 针对随机变化的 Level-1 系数,产生实证贝氏估计数(Empirical Bayes,EB)。实证贝氏估计数是透过.全部的资料来估计参数。更进一步说,Raudenbush 等认为“每个单位j 的 Level-1 系数的实证贝氏估计数是源自于两个来源的最佳组合:其一是基于该单位的数据所计算出来的估计值,其二是基于其他相似单位的数据所计算出来的估计值。直觉上,我们借用整体数据的优势来改善每个单位j 的 Level-1 系数估计数”(p.9)。因此,Level-1 系数的估计不是在每个单位j中独立地计算,而是基于全部数据所提供的信息计算的。Level-1系数估计方式的改善是相当重要的,因为 Level-1 系数是要被用来估计 Level-2 的固定效果(fixed effects)的。

第三, HLM 在估计 Level-2 固定效果时,使用广义最小二乘法 (generalized least squares,GLS,亦译为一般最小平方估计法)。固定效果可被视为是跨群体 Level-1 系数的加权平均,且通常被视为是预测因子与结果变量之间关系的估计数 (Hofmann, 1997)。广义最小二乘法优于普通最小二乘回归法之处在于其考量到每个群体所提供的信息精确度不一,亦即,有和较可信和和精确的 Level-1 估计数的群体,会获得更高的权重。


<a id="pdf-page-357"></a>
<!-- PDF页 357 -->

第四,HLM 提供了稳健的(robust)标准误估计数,即使HLM 的假设被违反(限于低限度的违反),此标准误估计数仍是一致的。因此,基于这些标准误估计数所做的假设检定统计推论是可信的,尤其当 Level-2 的样本数很大时(Bryk & Raudenbush, 1992).

第五,HLM 借由不平衡数据(unbalanced data,即每个群体的员工人数不同)的交互式计算(interactive computing) 技术,提供了方差协方差成分(variance-covariance components,亦译为变异共变因子)的有效估计数,这是传统的分析方法(如 ANCOVA)所无法达到的(Bryk and Raudenbush, 1992)。

### 3.2 研究问题与资料

我们在 Academy of Management Journal 上发表的论文(Liao and Chuang, 2004)使用了 HLM。该篇论文认为,服务业中顾客的满意度与组织的绩效息息相关,而服务人员在服务过程中与顾客的互动会影响到顾客所感受到的服务品质,因此,有必要进一步探究什么原因会影响员工的服务绩效,能提升组织绩效与顾客满意度。为此 Liao 和 Chuang建立了一个多层次的研究架构,来验证个人层次的因子与店层次的因子分别对员工服务绩效的影响,以及店层次的因子如何干扰个人层次的因子与员工服务绩效之间的关系;同时,亦将个人层次的员工服务绩效聚合为店层次的服务绩效,以分析店层次的服务绩效与顾客结果变项的关系。我们在此以该篇文章的部分数据,依据 Hofmann (1997)所提出的 HLM 分析程序,来进行实际操作分析。 由于原始文章的研究架构较复杂,变量也较多,因此,分析结果可能不会与原始文章的研究结果相同。图5 为示例的研究架构图。

图5 研究架构

在本例中,假设我们要检测的是影响员工个人服务绩效 (employee service performance)的自变量,此服务绩效是指员工在服务与帮助顾客的过程中,所表现出的满足顾客的需求与爱好的行为,因此,因变量为个人层次的服务绩效。在概念上,员工的服务绩效取决于员工个人的差异与情境因子,本例中,个人层次的因子即为外向性,而情境因子则为服务氛围。外向性(extraversion) 是五大人格因子之一,与个人善于社交、合群健将、积极的特质有关(Barrick and Mount, 1991),而服务氛围是指员工们对于政策、惯例以及受到奖励、支持与期望的顾客服务程序的共同知觉(Schneider, White and

Paul, 1998),因为服务氛围是员工们“共同的"知觉,所以将其设定为群体层次的构念,必须由同一群体中个别员工的知觉聚合而得。在此,我们假定分析的数据具有高组内SLES | 乡层次理论模型的建立及研究方法 | 343

![原书图示（PDF第357页）](../images/fig-p0357-1.jpg)


<a id="pdf-page-358"></a>
<!-- PDF页 358 -->

一致度,且员工对氛围的知觉有显著的组间差异,所以聚合是可行的。

基于人格和服务管理的文献,我们可以假设个人层次的外向性人格与群体层次的服务气候会正向地影响员工的服务绩效。进一步而言,已有学者认为人格与工作绩效之间的关系,并不一定对所有情境中的所有员工都会相同,所以,员工表现绩效时所处情境的强度已被认为会调解人格与员工行为之间的关系(如 Barrick and Mount, 1993; Mischel, 1977)。在强情境(strong situations)之下,对于员工如何表现出令人满意的行为会有较一致,清楚的规范。然而在弱情境(weak situations)之下,缺少一致、清楚的规范(Mischel, 1977)。因此,相较于员工在强情境中的行为,员工在弱情境之下在人格上的差异更可能会影响其表现的行为。此外,正向的服务气候可以通过主管在日常管理上不断地表现出对服务品质的重视,来创造出鼓励服务的氛围,因此,在强情境之下则限制了个人人格的表现。基于以上所述,我们假设服务氛围将会调节外向性与服务绩效之间的正向相关性,当服务氛围越正面时,此正向的相关性就会降低。在此,提出以下三个假设(hypotheses):

假设1:个人层次的外向性与员工的服务绩效呈现正相关;

假设2:群体层次的服务氛围与员工的服务绩效旦现正相关;

假设3:群体层次的服务氛围调节外向性与员工服务绩效之间的关系,以至于越正面的服务氛围,越会降低其正向的相关性。

接下来我们将使用在美国中西部的25 家连锁餐厅收集到的 257 位员工的样本,来探讨用以检验假设的 HLM 方程与统计检验。

Step I:零模型(Null Model)

由于我们假设个人层次的员工服务绩效可由个人层次与群体层次的变量来预测,所以必须显示出服务绩效在个人层次与群体层次上丝有变异存在,因此,第一个步骤要使用方差分析(ANOVA),将服务绩效的方差分成组内与组间方差。在此使用的 HLM估计的零模型是没有预测因子的,其模型如下:

Level-1 Model; 服务绩效; =By + ry

Level-2 Model; Bo = yo0 + Up;

在上述模型中,

Bw =第j个群体的服务绩效平均数

Yoo =服务绩效的总平均数

ry的方差 =o? =服务绩效的组内方差

Vo的方差 =7oo =服务绩效的组间方差

由于服务绩效的总方差 =o? + 7o,我们可依此计算出 ICC(1),即服务绩效组间方差的百分比,其公式如下:

ICC(1) = ro/ (0 + To)


<a id="pdf-page-359"></a>
<!-- PDF页 359 -->

此步骤分析结果为 ro。=0.35,且卡方检验的结果表明组间方差是显著的:x (24) = 58.45, p<0.001。 此外,o?=2.52,故ICC(1) =0. 12,表示员工服务绩效的方差有 12%是来自于组间方差,而 88%是来自于组内方差。

由于服务绩效具有显著的组间方差,接下来便可进行假设检验。

Step 11: 4239 (Rig 1B Level-1 的主效果

为了检验假设 1,我们将外向性加入 Level-1,并估计以下的模型:

Level-1 Model; 服务绩效; = Bo, +B, (SHITE) +r

Level-2 Model: Bo; = yoo + Ug;

Buy = 0 + U,,

在上述模型中,

Yoo = BEF AS AR PE IT HF HY He

Vio =跨群体斜率的平均数(用来检验假设 1)

ry的方差 =o* = Level-1 RH NAH

U6的方差 =7o。=截距的方差

UV的方差 =71, =斜率的方差

在上述模型中,yw与 yio分别代表 Level-1 的系数(即 Bw与 B,)跨群体的平均数,其中 yw是表示外向性与服务绩效跨群体的关系,因此可用来检验假设1。另外,HLM 亦对 yw与 yw进行:检验,如此便可检测这两个参数的统计显著性。此步骤的分析结果为yio =0.58, t-value (24) =43.68, p <0.001,因此,假设1 得到支持。

在 Level-1 的模型中,可通过加入外向性后组内方差减少的程度来计算 R*(此为一个 pseudo R?,即准 R平方),换言之,我们可计算出零模型中的组内方差有和多少百分比可被外向性解释,公式如下:

R’ for Level-1 model = (a from Step I - o” from Step II)/o” from Step I.

在这个例子中,Level-l 模型的 R® = (2.52 -2.23)/2.52 =0.12,表示服务绩效的组内方差(非总方差)有 12%可被外向性解释。

此外,在加入外向性后,ro。=4.52,卡方检验的结果显示此组间方差显著:x*(24) = 33.24, p <0.10,表示在 Level-2 模型中有可能存在群体层次的因子,因此,我们接下来检验假设 2。

Step II:检验 Level-2 的主效果

为了检验假设2,我们将服务氛围加入 Level-2,并佑计以下的以截距作为结果变量(intercepts-as-outcomes) 的模型;

Level-1 Model: 服务绩效; = Bo; + By(外向性;) +7;

Level-2 Model: Bo; = Yoo + Yo (服务氛围,) + Us;

By = 10 + Ui;

在上述模型中,


<a id="pdf-page-360"></a>
<!-- PDF页 360 -->

Yoo = Level-2 MARIE

Yor =加入外向性后,服务氛围对服务绩效的影响效果(用来检验假设 2)

yw =外向性对服务绩效的影响效果(用来检验假设 1)

的方差 =o” = Level-1 残差的方差

UV的方差 = Too = 截距残差的方差

UV的方差=71 =斜率的方差

上述模型中,yo是表示控制了 Level-1 的外向性后,服务氛围与员工服务绩效之间关系之估计数,对 yo进行;检验可用来检验假设2。此步骤的分析结果显示:yo, = 0.74, t-value (23) =0.74, p=0.012,因此,假设2 得到支持。

同 Step I,我们可以计算有多少百分比的服务绩效组间方差可以被服务氛围解释,其公式如下:

R? for Level-2 main effect model = (7T0 from Step I-79) from Step III) /7,, from Step II = (4.52 -4.09)/4.52 =0.10

结果显示,有 10% 的服务绩效组间方差(非总方差)可以被服务氛围解释。

此外,HLM 亦佑计了斜率(7) 的方差,并以卡方检验来检测此方差的显著性。结RRA rr, =0.19,久(24) =22.23, p >0.10,表示外向性与员工服务绩效之间的关系在各群体间没有显著的变异,换言之,假设3 将无法得到支持,因为检定假设3 WHE是和斜率的方差要显著。然而,为了便于示范,我们仍然进行调节效果的检验。

Step IV:检验假设 3 或调节效果

一般来说,为了检验 Level-l 变量与 Level-2 变量的交互作用,我们可以估计一个斜率作为结果变量(slopes-as-outcomes) 的模型,换言之,我们可以将 Level-2 的变量作为斜率系数(Bi;)的预测因子,以得知此,Level-2 的变量是否可以解释斜率的变异。其模型如下:

Level-1 Model: 服务绩效; = Bo + By(外向性;) tr

Level-2 Model: By; = Yoo + Yo (MRS FR HL;) + Uy

By; = V0 +7 ARS FR,) + Uy

在上述模型中,

Yoo = Level-2 的截距项(以 Level-1 Model 的截距为因变量)

Yo. = Level-2 的斜率

Yio = Level-2 的截距项(以 Level-1 Model 的斜率为因变量)

Yu =level-2 的斜率,即服务氛围对外向性与员工服务绩效关系之调节效果(用来检测假设 3)

ry的方差 =o” =Level-1 残差的方差

UV的方差 =7o = 截距残差的方差

V1的方差 =71 =斜率残差的方差


<a id="pdf-page-361"></a>
<!-- PDF页 361 -->

| 假设3 是预测服务氛围与外向性之间有负向的交互作用,以至于当存在高程度的服务氛围时,外向性与员工服务绩效之间的正向相关会降低。上述模型中,y,是表示服务氛围与外向性之间交互作用项的估计数,对 yi进行:检验可用来检测假设 3。此步TRY OT RAB AR:yi = -0.25, t-value (23) = -0.864, p >0.10,虽然交互作用的效果与假设3 预测的方向一致(即为负向的交互作用),但统计上不显著,因此,假设3 未得到支持。 |

假若读者想要计算斜率方差被服务氛围解释的程度,同样地,可以比较 Step IV 与Step I 的斜率残差方差,其公式如下: R? for Level-2 moderating model = (7, from Step III -7,, from Step IV)/7,, from Step III = (0.19 -0.19)/0. 19 =0结果显示,调节效果的 R 为0,此结果并不令人感到意外,因为交互作用的效果不BF.总之,HLM 的分析结果(见表1)为假设 1 与假设2成立,假设3不成立。表1 HLM 的分析结果变数 Step I Step II Step III Step IV截距项 (00) 9.33°° 7.32°* 4.86 °° 1.77 Level-1 预测因子外向性(yo) 0.58°* 0.59°* 1.40 Level-2 预测因子服务气候 (vo) 0.74° 1.68交互项外向性 x服务气候 Cy) -0.25方差a 2.52 2.23 2.22 2.23 To 0.35°° 4.52" 4.09" 4.22 Ty 0.20 0.19 0.19 R. Reet 0.12 River? waist" 0.10 Reeve 2 交世作用妆果“ 0 N(员工) =257, N(店) =25。“预测变量所对应到的数值为在稳健的标准误(robust standard errors)下的固定效果的估计数(ys)。* Riva: = (0 of null model or Step I ~ a” of Step II) /a” of null model. ° Reeve? est = (700 of null model or Step I ~ 79) of Step III) /r9) of null model. * Revs gntmmen = (Tu of Step Ill -7,, of Step IV)/r,, of Step IIL. tp <0.10

## 第十五章 | 多层次理论机型的建立及研究方法 | 347

![原书表格（PDF第361页）](../images/table-p0361-1.jpg)


<a id="pdf-page-362"></a>
<!-- PDF页 362 -->

### 3.4 HLM 的中心化问题(centering issues)

在 HLM 中,对于 Level-1 的预测因子有三个中心化的处理方法:

1. 原始尺度(raw metric):意即 Level-1 的预测因子是使用其原始的分数。当所有Level-1 预测因子的值为0 时,Level-1 的截距项即为结果变量的期望值。此外,截距项的方差(7) 即表示在控制住 Level-1 预测因子的效果之下,已调节过的(adiusted) 结果变量组间方差。

2. 总平均数中心化(grand-mean centering):是指每一个人的分数减去 Level-l 预测因子的总平均数。当所有 Level-1 的预测因子减去其各自的总平均数时,Level-l RE项即为在 Level-1 预测因子作总平均数中心化时,结果变量的期望值。此外,截距项的方差(7o)即表示在控制住 Level-1 预测因子的效果之下,已调节过的结果变量组间方差。

3. 组内平均数中心化(group-mean centering):是将每一个人的分数减去 Level-1 预测因子的组别平均数。当所有 Level-1 的预测因子减去其各自的组别平均数时,Level-1

。 的截距项即为在 Level-1 预测因子作组别平均数中心化时,结果变量的期望值。此外,截距项的方差(7o) 即表示在没有控制住 Level-1 预测因子的效果之下,未调节过的(unadjusted) 结果变量组间方差。

HLM 的中心化处理是个比较复杂的议题,且已有许多研究者探讨过中心化会如何影响 HLM 的统计估计与解释(如 Bryk and Raudenbush, 1992; Hofmann and Gavin, 1998)。例如,Hofmann 和 Gavin 对于 Level-1 的预测因子使用以上三种中心化的处理方法上的意涵有很详细的说明,我们鼓励有兴趣的读者详阅他们的著作。基于 Hofmann和 Gavin 的研究,在此列出关于 Level-1 的预测因子在中心化处理上的一些基本知识及

1. 使用原始尺度与总平均数中心化这两种方法,会产生两个等同的模型,但组别平均数中心化的处理结果却不等同于这两个方法。

2. 假若要检测 Level-1 预测因子的主效果,对 Level-1 预测因子使用原始尺度或总平均数中心化都是适当的处理方法。在我们的例子中,为了检测假设 1,我们可以选择使用原始尺度或总平均数中心化来处理 Level-1 的外向性,以估计外向性对服务绩效的影响效果。

3. 假若要在控制住 Level-1 预测因子的效果之下,检测 Level-2 预测因子的主效果,对 Level-1 预测因子使用原始尺度或总平均数中心化处理都是适当的。在我们的例子中,为了检测假设2,我们可以选择使用原始尺度或总平均数中心化来处理 Level-1 的外向性,以估计在控制住外向性的效果之下,服务氛围对服务绩效的影响效果。

4. 在估计 Level-2 预测因子的主效果时,假若对 Level-1 的预测因子使用组别平均数中心化来处理,则 HLM 将无法控制住 Level-1 预测因子的效果。所以,为了能够适当


<a id="pdf-page-363"></a>
<!-- PDF页 363 -->

地控制住 Level-1 预测因子的效果,必须将 Level-1 预测因子的组别平均数加入 Level-2作为控制变量。在我们的例子中,假若我们使用组别平均数来中心化 Level-1 的外向性,则必须将外向性的组别平均数与 Level-2 的服务氛围一起加入 Level-2 作为控制变量,如此才能体现在控制了外向性的影响之后,服务氛围对员工服务绩效的效果。5. 假若要检测 Level-1 预测因子与 Level-2 预测因子之间交互作用的效果,使用原始尺度或总平均数中心化来处理 Level-1 的预测因子丝可。然而,因为在这两个处理方法之下所产生的 Level-1 斜率包含了组内与组间的关系,所以,跨层次交互作用(crosslevel interaction) 的效果可能会是假性的(spurious)。因此,为了估计到真实的跨层次交互作用的效果,Hofmann 和 Gavin (1998)建议较佳的处理方法是估计下列的模型,在此模型中,Level-1 的预测因子是使用组别平均数中心化来处理,并将组别平均数加入 Level-2 作为控制变量。另外,我们明确地控制组间交互作用 (between-group interaction) 的效果。在我们的例子中,即是将“外向性的组别平均数 x 服务氛围"视为 Level-2 的控制变量,以能控制住组间交互作用的效果,在我们的例子中,其模型为: Level-1: 服务绩效; = Bo + By (PPA Ee essere ny) try Level-2: Bo; = Yoo + Yo (外向性的组别平均数,) + yo(服务氛围,) | +Yo(外向性的组别平均数 x服务氛围), + Us, By =Ywo +Yu(服务氛围,) + U,,上述模型中,pi,是外向性与服务绩效之间组内关系的估计数,而 yi是在外向性与服务氛围的主效果被适当地解释下,所估计到的真实的跨层次交互作用效果的估计数。Hofmann 和 Gavin (1998)建议在实际操作时,可在估计跨层次交互作用的效果时,对 Level-1 的因子使用原始尺度或总平均数中心化来处理,接着再使用组别平均数中心化来再重新估计一次模型(组别平均数需被加入 Level-2 作为控制变量),然后,观察这两个模型所估计到的 y,参数值是否相同,若是,研究者就可以呈现使用原始尺度或总平均数中心化处理后的分析结果,并注明已使用组别平均数中心化双重确认过,以证明分析结果不是假性的。而我们认为,只要在 Level-2 控制住“外向性的组别平均数”和“外向性的组别平均数 x 服务氛围,那么即使 Level-1 的预测因子使用总平均数中心化,yu所估计到的也还是真实的跨层次交互作用效果的估计数。见如下模型: Level-1: 服务绩效; = Bo; + Bi(外向性qty) +r; Level-2: Bo; = yoo + Yo(外向性的组别平均数,) + Yoo (服务氛围,) +Yo(外向性的组别平均数 x服务氛围), + Uy, By =Yw +Yu(服务氛围,) + U,,上述模型中,既然组间交互作用(即 y。,) 已被明确地控制住,y,,所代表的应该是真实的跨层次交互作用效果的估计数。以上方法的另外一个优点是, 如 Hofmann 和Gavin (1998)所指出的, 既然我们一般会使用原始尺度或总平均数中心化来检测主效果,那么车以相同的方法来检测交互作用的效果,相信对读者而言应该是比较容易理解2t2R | 多层次理论模型的建立及研究方法 | 349


<a id="pdf-page-364"></a>
<!-- PDF页 364 -->

的。Liao 和 Chuang (2007)也是使用以上方法来检测个人体验到的转换型领导风格与店层次服务氛围的跨层次交互作用对员工服务绩效的效果。在他们的例子中,Level-l的预测因子,即领导风格,使用的是总平均数中心化;他们在 Level-2 控制领导风格的组别平均数以及“领导风格的组别平均数 x 服务氛围”。 |

总体而言, 选择以总平均数或组别平均数来作中心化的处理,应该要有理论的支持(Kreft, de Leeuw and Aiken, 1995),

此外,HLM 对 Level-2 的预测因子亦有两个中心化的处理方法:

1. 原始尺度:意即 Level-2 的预测因子是使用其原始的分数。

2. 总平均数中心化:是指每一群体平均的分数减去 Level-2 预测因子的总平均数。

对于 Level-2 中心化处理的估计与解释意涵很少被探讨到,而 Bryk 和 Raudenbush《1992)认为 Level-2 预测因子的中心化处理议题并不如 Level-1 预测因子一样重要,他们同时也提到“使用总平均数来对所有 Level-2 的预测因子进行中心化处理通常也是很实用、方便的”(p.29)。

Bryk 和 Raudenbush (1992)提到典型的二阶线性 HLM 模型必须有下列的统计假设:

1. 在每个 Level-2 单位中的每个 Level-1 单位,Level-1 的残差项彼此独立、呈现正态分布,且有零均值.方差为 0?。

2. Level-1 的预测因子与 Level-1 的残差项互为独立。

3. Level-2 的随机误差项旦现多元正态分布,且缘有零均值、方差 7,,及共变量 Tags并且彼此独立。

4. Level-2 的预测因子与 Level-2 的残差项互为独立。

5. Level-1 的残差项与 Level-2 的残差项互为独立。.

Bryk 和 Raudenbush (1992)对上述的基本假设与违反假设的可能影响有一些探讨。因为 HLM 仍是一个正在发展的分析方法,我们尚无法清楚知道 HLM 分析对这些基本假设的违反在多大程度上不受影响。

### 3.6 HLM 分析所需的样本数

ALM 与其他统计分析方法一样,样本数越大,估计数越精确,统计检验力越高。假车要进行二阶层的 HLM 分析,不只需要很大的群体样本数,且每个群体中要有足够的个人样本数,但要取得很大的样本数是耗时又费力的,因此,我们必须了解进行 HLM 分析所需的样本数。然而 Hofmann 等(2000)提到,对于究竟要多少样本数,才能达到适当的统计检验力与无偏误的分析结果,仍然有许多事要探讨。Hofmann 等(2002)、Bassiri (1988) 55 van der Leeden 和 Busing (1994)认为在检测跨层次交互作用的效果时,为了


<a id="pdf-page-365"></a>
<!-- PDF页 365 -->

达到 0.90 的统计检验力,必须有 30 个群体样本数,且每个群体包含 30 个个人样本数。然而,在典型的组织管理研究中,群体数通常比较小,但比较欣奈的是有较大的 Level-2样本数,可以弥补Level-l 小样本数在统计检验力上的不足。例如,假若有150 个群体样本数,在维持相同的检验力之下,每个群体中所需的个人样本数就可以降低。

Maas 和Hox (2005) 的模拟研究检测 Level-2 与 Level-1 在不同样本数的情况之下,对多层次分析中的估计值(指回归系数与方差)与其标准误的影响。结果显示,只有在Level-2 为小样本时(小于或等于50 个样本),会导致对第二个层次的标准误有偏误的估计,而在其余的模拟情况下(如 Level-1 为小样本),回归系数、方差以及标准误的估计和芝无偏误且正确。

### 3.7 HLM 三阶层与广义型线性模型

接下来,我们将讨论二阶层 HLM 分析的两个延伸议题。

延伸议题1:三阶层 HLM 分析(HLM3)

我们已讨论过线性阶层模型的二阶层分析,而将二阶层模型扩充的方法之一就是增加另一个阶层。例如,假车我们所收集的样本数据是每个人被包含在不同的团队中,而这些团队又被包含在不同的组织中,即会呈现一个三阶层的数据结构。HLM 软件亦可以进行三阶层的分析。. ‘

举例来说,Joshi, Liao 和 Jackson (2006)从财富 500 强中的一家公司中挑选出46 个业务单位,再针对这 46 个单位的437 个团队中的3318 位业务员进行样本数据的收集,并使用三阶层的 HLM 来分析,以检测工作团队的人口统计特征组成与工作单位的管理人口组成会如何调节个人的人口统计特征(性别与种族)与薪资水准之间的关系。结果发现,团队中有色人种的比例越高, 因种族而衍生的薪资水准不平等现象越少;而工作单位中的管理阶层为女性与有色人种的比例越高,因性别与种族而衍生的薪资水准不平等现象越少。此外,结果亦发现绩效会部分中介于个人人口特性、团队人口组成及管理人口组成与薪资水准之间的关系。

延伸议题 2: 多层广义型线性模型(Hierarchical Generalized Linear Models, or HGLM)

前述的二阶层与三阶层 HLM 分析是适用于在每一个阶层的随机效果是呈现正态分布的阶层数据,然而,在某些例子中,Level-1 呈现正态分布的假设是不真实的,且也不容易以变量的转换来达到。以下为四个违反正态分布的典型例子:

1. 结果变量为二元变量(binary variable)。例如,员工是否已经离开公司(1 =高

职;0 =仍在职),这是在研究员工流动率时,典型的结果变量,在此例子中,Level-1 的残.差项只会产生两个值的一个,因此无法呈现正态分布,而 Level-1 的残差项也无法有同方差(homogeneous variance)。 垩者,在标准模型中,Level-1 结果的预测值并没有范围限制,因此,我们可能会得到大于 1 或小于0 的预测值,与真实情况不符,因为Y不可超过. SES | 多层次理论模型的建立及研究方法 | 351


<a id="pdf-page-366"></a>
<!-- PDF页 366 -->

[0, 1]的区间。

2. 结果变量包含计数数据(count data)或非负整数(non-negative integers)0、1、2...,数据中有许多的0 值。例如,在研究工作场所的安全时,典型的结果变量为职业伤害的员工人数,此例中,因为存在许多0 值(即许多员工都没有职业伤害),所以正态分布无法以变量的转换来呈现。且 Level-1 的残差项不会有同方差,相反必须视预测值而定(高预测值将会有大的方差),同样地,预测值也有可能会超出范围(即可能会有负的预测值)。

3. 结果变量为多项式变量(multinomial variable)或包含多个(>2)类别。例如,业务员有多个不同的薪资计划可以选择:1 =纯粹时薪制;2 =纯粹佣金制;3 = BAMHS佣金制。狂如先前所讨论过的二值结果变量的模型,使用标准的 HLM 来分析多项式模型会不太适当。

4. 结果变量为序数变量(ordinal variable)或包含多个次序类别。例如,顾客再度购买的意愿:1 =不会,我将不会再购买此产品;2 =不确定;3 =会,我将会再购买此产品。在此例中,顾客再度购买的意愿是从负的、中立到正的,因此是有次序的,所以,如同二值结果变量的模型,使用标准的 HLM 来分析序列模型会不太适当。

在 HLM 软件中,使用者可以设定为非线性分析或多层广义型线性模型(HGLM),以能适当地分析二值的、可数的、多项式的以及序数的数据形态之模型,而这些模型相当于在非阶层统计分析中所探讨的 logit 模型(logit model)、泊松模型(Poisson model)、多项式模型(multinomial model) 以及序数模型(ordinal model)。讨论 HGLM 的细节已超越本章的介绍范围,有兴趣的读者可以参考 HLM 手册(Raudenbush, Bryk, Cheong and Congdon, 2004),其对 HGLM 的概念、统计背景以及分析的例子绰有详细的说明。

### 3.8 HLM 的局限性

虽然 HLM 在分析多层次的数据上,已相当普及且有许多优点,但如同其他统计分析方法一样,HLM 也有一些局限性,Bryk 和 Raudenbush (1992)、Hofmann 等(2000)与James 和 Williams (2000)等学者已探讨了这些局限性。. 例如,James # Williams 认为当样本数很大、方程式设定正确且变量有信度时,HLM 可以比传统的回归分析更有效地估计参数。然而,假若前述的条件有一个或更多个未被满足,则估计可能会有问题,分析结果可能无法复制,而且其中一个方程式的设定误差(specification errors) 可能会影响到整个模型。因此,对于 HLM 的估计值有多稳健与稳定,有更多的检测等着去完成。此外,James 和 Williams 主张:“有些时候使用较不复杂的分析程序(如 OLS) SE, AW这些分析方法较稳定,且能够使方程式的设定误差不影响到其他方程式。” |

总而言之, HLM 最适合用来检验预测因子跨越许多阶层(HLM 最高可到三阶层,但有些软件,如 Min 这个软件(Rasbash and Woodhouse, 1995) 可以分析三阶层以上的模型)但结果变量是在较低分析层次的跨层次模型,犹如 Hofmann 等(2000)所提到的,


<a id="pdf-page-367"></a>
<!-- PDF页 367 -->

HLM 无法有效地检测较低层次的预测因子对较高层次的结果变量之影响。四、结 8

随着近来管理与组织行为研究在理论与方法论上的进展,我们发现有越来越多的研究综合了微观与宏观的观点,以检测多层次的因子在不同分析层次时如何相互影响或结合来影响结果变量。此类的多层次研究提供了“对组织生命更深沉、更丰定的描述——也就是承认组织情境会影响个人的行为与知觉,而个人的行为与知觉也会影响组织情境"(Klein et al., 1999: 243)。在此章节,我们先针对多层次理论的建立、多层次模型的不同类型以及多层次分析技术的关键要素作了简要的浏览,然后再详细探讨多层次分析中的数据聚合问题,且以 HLM 为例作了跨层次模型的分析。最后,我们想基于几年来从事多层次研究和教学的经验,提出以下几点心得供读者参考:首先,学者们常有疑问何时该使用 HLM 这个软件,这可分为理论导向和数据导向两种时机。理论导向是指当研究的架构是跨层次模型,也就是说其目的是在探讨高层次构念对低层次构念的影响时,即可使用 HLM;而数据导向是指,当理论架构只有单一层次(即预测因子与结果变量都是在较低分析层次、没有涵盖高层次的构念)时,车数据的结构为集状(例如,员工嵌套于组织中),亦可使用 HLM 来解决数据违反普通最小二乘回归法独立性假设(independence assumption)的问题。我们呼吁对多层次研究有兴趣的学者,不要因为HLM 看似繁杂而放弃使用它——其实 HLM 只是回归方法的延伸。然而,常有学者因为HLM 为近来受青睐的分析工具,而将原本只是单一层次的研究架构或数据,硬是以多层次的手法处理,这样的结果会使得学者原本有兴趣的研究现象无法获得解答。故我们建议学者分析数据时应使用最适合的工具,而非最近流行的工具。再者,多层次研究的理论与模型的应用并不仅限于组织管理领域中,它已经在教育和医学领域行之有年,其他管理领域虽然较少使用,但如行销管理.策略管理仍有极多研究问题可以此方法来控讨,而且就我们所知这些学者也对使用这种工具很有兴趣。在此,我们鼓励学者将多层次理论与方法应用在中国的管理研究上,也希望本章能够对多层次理论与方法的推广有些帮助。

参考文献.

Barrick, M. R. and Mount, M. K. (1991). The Big Five personality dimensions and job performance: A meta-analysis. Personnel Psychology, 44, 1—26.

Barrick, M. R. and Mount, M. K. (1993). Autonomy as a moderator of the relationships between the Big Five personality dimensions and job performance. Journal of Applied Psychology, 78, 111—118.

SEER | 多层次理论模型的建立及研究方法 | 353


<a id="pdf-page-368"></a>
<!-- PDF页 368 -->

Bartko, J. J. (1976). On various intraclass correlation reliability coefficients. Psychological Bulletin, 83, 762—765.

Bassiri, D. (1988). Large and small sample properties of maximum likelihood estimates for the hierarchical linear model. Unpublished doctoral dissertation, Michigan State University.

Bliese, P. D. (1998). Group size, ICC values, and group-level correlations; A simulation. Organizational Research Methods, 1, 355—373.

Bliese, P. D. (2000). Within-group agreement, non-independence, and reliability; Implications for data aggregation and analysis. In K. J. Klein and S. W. J. Kozlowski (eds.), Multilevel Theory, Research, and Methods in Organizations; Foundations, Extensions, and New Directions; 349-381. San Francisco; Jossey-Bass.

Bliese, P. D. and Halverson, R. R. (1996). Individual and nomothetic models of job stress; An examination of work hours, cohesion, and well-being. Journal of Applied Social Psychology, 26, 1171—1189.

Bliese, P. D., Halverson, R. R. and Rothberg, J. M. (1994). Within-group agreement scores: Using resampling procedures to estimate expected variance. Academy of Management Best Paper Proceedings, 303—307.

Bliese, P. D. and Hanges, P. J. (2004). Being both too liberal and too conservative; The perils of treating grouped data as though they were independent. Organizational Research Methods, 7, 400—417.

Bryk, A. S. and Raudenbush, S. W. (1992). Hierarchical Linear Models; Applications and Data Analysis Methods. California; Sage publication.

Chan, D. (1998). Functional relations among constructs in the same content domain at different levels of analysis; A typology of composition models. Journal of Applied Psychology, 83, 234—246.:

Chen, G. and Bliese, P. D. (2002). The role of different levels of leadership in predicting self- and collective efficacy; Evidence for discontinuity. Journal of Applied Psychology, 87, 549—556.

Dansereau, F., Alutto, J. and Yammarino, F. (1984). Theory Testing in Organizational Behavior; The Varient Approach. Englewood Cliffs, NJ: Prentice Hall.

Dansereau, F. and Yammarino, F. J. (2000). Within and between analysis; The varient paradigm as an underlying approach to theory building and testing. In K. J. Klein and S.. W. J. Kozlowski (eds.), Multilevel Theory, Research, and Methods in Organizations; Foundations, Extensions, and New Directions; 425—466. San Francisco: Jossey-Bass.

DeShon, R. P., Kozlowski, S. W., Schmidt, A. M., Milner, K. R. and Wiech-


<a id="pdf-page-369"></a>
<!-- PDF页 369 -->

mann, D. (2004). A multiple-goal, multilevel model of feedback effects on the regulation of individual and team performance. Journal of Applied Psychology, 89, 1035—1056.

Ehrhart, M. G. (2004). Leadership and procedural justice climate as antecedents of unit-level organizational citizenship behavior. Personnel Psychology, 57, 61—94.

George, J. M. (1990). Personality, affect, and behavior in groups. Journal of Applied Psychology, 75, 107—116.

George, J. M. and James, L. R. (1993). Personality, affect, and behavior in groups revisited; Comment on aggregation, levels of analysis, and a recent application of within and between analysis. Journal of Applied Psychology, 78, 798—804.

Hofmann, D. A. (1997). An overview of the logic and rationale of hierarchical linear models. Journal of Management, 23, 723—744.

Hofmann, D. A. and Gavin, M. B. (1998). Centering decisions in hierarchical linear models; Implications for research in organizations. Journal of Management, 24, 623—641.

Hofmann, D. A., Griffin, M. A. and Gavin, M. B. (2000). The application of hierarchical linear modeling to organizational research. In K. J. Klein and S. W. J. Kozlowski (eds.), Multilevel Theory, Research, and Methods in Organizations; Foundations, Extensions, and New Directions; 467—511. San Francisco: Jossey-Bass.

Hofmann, D. A., Morgeson, F. P. and Gerras, S. J. (2003). Climate as a modera-

' tor of the relationship between leader-member exchange and content specific citizenship; Safety climate as an exemplar. Journal of Applied Psychology, 88, 170—178.

James, L. R. (1982). Aggregation bias in estimates of perceptual agreement. Journal

of Applied Psychology, 67, 219—229. | - James, L. R., Demaree, R. G. and Wolf, G. (1984). Estimating within-group interrater reliability with and without response bias. Journal of Applied Psychology, 69, 85—98.

James, L. R., Demaree, R. G. and Wolf, G. (1993). r,,: An assessment of withingroup interrater agreement. Journal of Applied Psychology, 78, 306—309.

James, L. R. and Williams, L. J. (2000). The cross-level operator in regression, ANCOVA, and contextual analysis. In K. J. Klein and S. W. J. Kozlowski (eds.), Multilevel Theory, Research, and Methods in Organizations; Foundations, Extensions, and New Directions; 382—424,. San Francisco; Jossey-Bass.

Joshi, A., Liao, H. and Jackson, S. E. (2006). Cross-level effects of workplace diversity on sales performance and pay. Academy of Management Journal, 49, 1—23.

Klein, K. J., Dansereau, F. and Hall, R. J. (1994). Levels issues in theory development, data collection, and analysis. Academy of Management Review, 19, 195—229.

Klein, K. J. and Kozlowski, S. W. J. (2000). Multilevel Theory, Research, and


<a id="pdf-page-370"></a>
<!-- PDF页 370 -->

Methods in Organizations: Foundations, Extensions, and New Directions. San Francisco: Jossey-Bass.

Kozlowski, S. W. J. and Hattrup, K. (1992). A disagreement about within-group agreement: Disentangling issues of consistency versus consensus. Journal of Applied Psychology, 77, 161—167.

Kozlowski, S. W. J. and Hults, B. M. (1987). An exploration of climates for technical updating and performance. Personnel Psychology, 40, 539—562.

; Kozlowski, S. W. J. and Klein, K. J. (2000). A multilevel approach to theory and research in organizations; Contextual, temporal, and emergent processes. In K. J. Klein and S. W. J. Kozlowski (eds.), Multilevel Theory, Research, and Methods in Organizations; Foundations, Extensions, and New Directions; 3—90. San Francisco; Jossey-Bass.

Kreft, I. G. G., de Leeuw, J. and Aiken, L. S. (1995). The effect of different forms of centering in hierarchical linear models. Multivariate Behavioral Research, 30, 1—21.

Liao, H. and Chuang, A. (2004). A multilevel investigation of factors influencing employee service performance and customer outcomes. Academy of Management Journal, 47, 41—58.

Liao, H. and Chuang, A. (2007). Transforming service employees and climate; A multi-level multi-source examination of transformational leadership in building long-term service relationships. Journal of Applied Psychology, 92, 1006—1019.

Lindell, M. K. and Brandt, C. J. (2000). Climate quality and climate consensus as mediators of the relationship between organizational antecedents and outcomes. Journal of Applied Psychology, 85, 331—348.

Maas, C. J. M. and Hox, J. J. (2005). Sufficient sample sizes for multilevel modeling. European Journal of Research Methods for the Behavioral and Social Sciences, 1, 86-92.

Mischel, W. (1977). The interaction of person and situation. In D. Magnusson and N. S. Endler (eds.), Personality at the Crossroads; Current Issues in Interactional Psychology: 333—352. Hillsdale, NJ; Erlbaum.

Muthen, B. (1994). Multilevel covariance structure analysis. Sociological Methods and Research, 22, 376—398.

Rasbash, J. and Woodhouse, G. (1995). MIn command reference. London: University of London, Institute of Education.

Raudenbush, S. W., Bryk, A. S., Cheong, Y. F. and Congdon, Jr., R. T. (2004). HLM6: Hierarchical Linear and Nonlinear Modeling. IL; SSI.

Schneider, B. (1987). The.people make the place. Personnel Psychology, 40, ~


<a id="pdf-page-371"></a>
<!-- PDF页 371 -->

SS 437—453. |

Schneider, B., White, S. S. and Paul, M. C. (1998). Linking service climate and customer perceptions of service quality; Test of a causal model. Journal of Applied Psychology, 83, 150—163.

Siebert, S. E., Silver, S. R. and Randolph, W. A. (2004). Taking empowerment to the next level; A multiple-level model of empowerment, performance, and satisfaction. Academy of Management Journal, 47, 332—349.

Statistical Sciences (1997). S-PLUS 4.0 Guide to Statistics. Seattle; Mathsoft.

van der Leeden, R. and Busing, F. M. T. A. (1994). First iteration versus igls/rigls estimates in two-level models; A Monte Carlo study with ML3. Psychometrics and Research Methodology, preprint PRM, 94—03.

Yammarino, F. J. and Markham, S. E. (1992). On the application of within and between analysis; Are absence and affect really group-based phenomena? Journal of Applied Psychology, 77, 168—176.

BEER | 多层次理论模型的建立及研究方法 | 357


