<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xd="http://www.oxygenxml.com/ns/doc/xsl"
    xmlns:hl7="urn:hl7-org:v3"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:xhtml="http://www.w3.org/1999/xhtml"
    xmlns:sdtc="urn:hl7-org:sdtc"
    xmlns="http://www.w3.org/1999/xhtml"
    exclude-result-prefixes="xd hl7 xsi xhtml sdtc">
    <xd:doc scope="stylesheet">
        <xd:desc>
            <xd:p><xd:b>Title:</xd:b> CDA R2 StyleSheet</xd:p>
            <xd:p><xd:b>Version:</xd:b> 4.1.0-beta.2</xd:p>
            <xd:p><xd:b>Maintained by:</xd:b> HL7 <xd:a href="https://confluence.hl7.org/display/SD/Structured+Documents">Structured Documents Work Group</xd:a></xd:p>
            <xd:p><xd:b>Purpose:</xd:b> Provides general purpose display of CDA release 2.0 and 2.1 (Specification: ANSI/HL7 CDAR2) and CDA release 3 (Specification was pulled after ballot) documents. It may also be a starting point for people interested in extending the display. This stylesheet displays all section content, but does not try to render each and every header attribute. For header attributes it tries to be smart in displaying essentials, which is still a lot.</xd:p>
            <xd:p><xd:b>License:</xd:b> Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at <a href="http://www.apache.org/licenses/LICENSE-2.0">http://www.apache.org/licenses/LICENSE-2.0</a></xd:p>
            <xd:p><xd:b>Warranty</xd:b> The CDA XSL is a sample rendering and should be used in that fashion without warranty or guarantees of suitability for a particular purpose. The stylesheet should be tested locally by implementers before production usage.</xd:p>
            <xd:p><xd:b>Project Link:</xd:b> <xd:a href="https://github.com/HL7/cda-core-xsl">https://github.com/HL7/cda-core-xsl</xd:a>. Including downloads of releases, documentation, issue tracker and more.</xd:p>
            <xd:p><xd:b>History:</xd:b> This stylesheet stands on the shoulders of giants. The stylesheet is the cumulative work of several developers; the most significant prior milestones were the foundation work from HL7 Germany and Finland (Tyylitiedosto) and HL7 US (Calvin Beebe), and the presentation approach from Tony Schaller, medshare GmbH provided at IHIC 2009. The stylesheet has subsequently been maintained/updated by Lantana Group (US) and Nictiz (NL).</xd:p>
            <xd:p><xd:b>Revisions:</xd:b> The release notes previously contained in the stylesheet, have moved to the <xd:a href="https://github.com/HL7/cda-core-xsl/wiki/Revisions">GitHub</xd:a> where the project is maintained.</xd:p>
        </xd:desc>
    </xd:doc>
    
    <xd:doc>
        <xd:desc>
            <xd:p>Use XHTML 1.0 Strict with UTF-8 encoding. CDAr3 specifies an XHTML subset of tags in Section.text so that makes mapping easier.</xd:p>
        </xd:desc>
    </xd:doc>
    <xsl:output method="xml" encoding="utf-8" omit-xml-declaration="yes" indent="no"/>

    <xd:doc>
        <xd:desc>
            <xd:p>Main template. Triggers on all top level ClinicalDocument elements</xd:p>
        </xd:desc>
    </xd:doc>
    <xsl:template match="/">
        <xsl:for-each select="hl7:section">
            <xsl:call-template name="section-text"/>
        </xsl:for-each>
    </xsl:template>
    
    <xd:doc>
        <xd:desc>
            <xd:p>Puts a div around the Section.text and hands it off to other templates</xd:p>
        </xd:desc>
    </xd:doc>
    <xsl:template name="section-text">
        <div><xsl:apply-templates select="hl7:text"/></div>
    </xsl:template>

    <xd:doc>
        <xd:desc>
            <xd:p>Handle observationMedia</xd:p>
        </xd:desc>
    </xd:doc>
    <xsl:template match="hl7:observationMedia">
        <xsl:variable name="renderID">
            <xsl:choose>
                <xsl:when test="@ID">
                    <xsl:value-of select="@ID"/>
                </xsl:when>
                <xsl:otherwise>
                    <xsl:value-of select="concat(generate-id(.), '_', local-name(.))"/>
                </xsl:otherwise>
            </xsl:choose>
        </xsl:variable>
        <xsl:variable name="renderAltText">
            <xsl:if test="hl7:id">
                <xsl:value-of select="concat(hl7:id[1]/@root, ' ', hl7:id[1]/@extension)"/>
            </xsl:if>
        </xsl:variable>
        <xsl:variable name="renderElement" select="self::hl7:observationMedia/hl7:value"/>
        <xsl:choose>
            <xsl:when test="$renderElement/hl7:reference[starts-with(translate(normalize-space(@value),'JAVASCRIPT','javascript'),'javascript')]">
                <pre title="{$renderAltText}">
                    <b><i><xsl:value-of select="$renderElement/hl7:reference/@value"/></i></b>
                </pre>
            </xsl:when>
            <!-- if there is a reference, use that in an iframe -->
            <xsl:when test="$renderElement/hl7:reference">
                <xsl:variable name="source" select="string($renderElement/hl7:reference/@value)"/>
                <xsl:choose>
                    <xsl:when test="$renderElement[starts-with(@mediaType, 'image/')]">
                        <img alt="{$renderAltText}" title="{$renderAltText}" src="{$source}">
                        </img>
                    </xsl:when>
                    <xsl:otherwise>
                        <iframe name="{$renderID}" id="{$renderID}" width="100%" height="600" title="{$renderAltText}">
                            <xsl:if test="$renderElement/@mediaType != 'application/pdf'">
                                <xsl:attribute name="sandbox"/>
                            </xsl:if>
                            <xsl:attribute name="src">
                                <xsl:value-of select="$source"/>
                            </xsl:attribute>
                            <xsl:text> </xsl:text>
                        </iframe>
                    </xsl:otherwise>
                </xsl:choose>
            </xsl:when>
            <!-- This is an image of some sort -->
            <xsl:when test="$renderElement[starts-with(@mediaType,'image/')]">
                <img alt="{$renderAltText}" title="{$renderAltText}">
                    <xsl:attribute name="src">
                        <xsl:value-of select="concat('data:',$renderElement/@mediaType,';base64,',$renderElement/text())"/>
                    </xsl:attribute>
                </img>
            </xsl:when>
            <xsl:when test="$renderElement[@representation = 'B64']">
                <iframe name="{$renderID}" id="{$renderID}" width="100%" height="600" title="{$renderAltText}">
                    <xsl:if test="$renderElement/@mediaType != 'application/pdf'">
                        <xsl:attribute name="sandbox"/>
                    </xsl:if>
                    <xsl:attribute name="src">
                        <xsl:value-of select="concat('data:', $renderElement/@mediaType, ';base64,', $renderElement/text())"/>
                    </xsl:attribute>
                    <xsl:text> </xsl:text>
                </iframe>
            </xsl:when>
            <!-- This is plain text -->
            <xsl:when test="$renderElement[not(@mediaType) or @mediaType='text/plain']">
                <pre title="{$renderAltText}">
                    <xsl:value-of select="$renderElement/text()"/>
                </pre>
            </xsl:when>
            <xsl:otherwise>
                <!-- Cannot display the text -->
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <xd:doc>
        <xd:desc>
            <xd:p>Handle    paragraph  </xd:p>
        </xd:desc>
    </xd:doc>
    <xsl:template match="hl7:paragraph">
        <p>
            <xsl:apply-templates select="." mode="handleSectionTextAttributes"/>
            <xsl:apply-templates/>
        </p>
    </xsl:template>

    <xd:doc>
        <xd:desc>
            <xd:p>Handle    linkHtml  </xd:p>
        </xd:desc>
    </xd:doc>
    <xsl:template match="hl7:linkHtml">
        <xsl:element name="a">
            <xsl:apply-templates select="." mode="handleSectionTextAttributes">
                <xsl:with-param name="class">linkHtml</xsl:with-param>
            </xsl:apply-templates>
            <xsl:apply-templates/>
        </xsl:element>
    </xsl:template>

    <xd:doc>
        <xd:desc>
            <xd:p>Handle pre</xd:p>
        </xd:desc>
    </xd:doc>
    <xsl:template match="hl7:pre">
        <pre>
            <xsl:apply-templates/>
        </pre>
    </xsl:template>

    <xd:doc>
        <xd:desc>
            <xd:p>Handle content. Content w/ deleted text is hidden</xd:p>
        </xd:desc>
    </xd:doc>
    <xsl:template match="hl7:content">
        <span>
            <xsl:apply-templates select="." mode="handleSectionTextAttributes"/>
            <xsl:apply-templates/>
        </span>
    </xsl:template>

    <xd:doc>
        <xd:desc>
            <xd:p>Handle line break </xd:p>
        </xd:desc>
    </xd:doc>
    <xsl:template match="hl7:br">
        <xsl:element name="br">
            <xsl:apply-templates/>
        </xsl:element>
    </xsl:template>

    <xd:doc>
        <xd:desc>
            <xd:p>Handle list  </xd:p>
        </xd:desc>
    </xd:doc>
    <xsl:template match="hl7:list">
        <!-- caption -->
        <xsl:if test="hl7:caption">
            <div style="font-weight:bold; ">
                <xsl:apply-templates select="hl7:caption"/>
            </div>
        </xsl:if>
        <!-- item -->
        <xsl:choose>
            <xsl:when test="@listType='ordered'">
                <ol>
                    <xsl:apply-templates select="." mode="handleSectionTextAttributes"/>
                    <xsl:for-each select="hl7:item">
                        <li>
                            <xsl:apply-templates select="." mode="handleSectionTextAttributes"/>
                            <xsl:apply-templates/>
                        </li>
                    </xsl:for-each>
                </ol>
            </xsl:when>
            <xsl:otherwise>
                <!-- list is unordered -->
                <ul>
                    <xsl:apply-templates select="." mode="handleSectionTextAttributes"/>
                    <xsl:for-each select="hl7:item">
                        <li>
                            <xsl:apply-templates select="." mode="handleSectionTextAttributes"/>
                            <xsl:apply-templates/>
                        </li>
                    </xsl:for-each>
                </ul>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <xd:doc>
        <xd:desc>
            <xd:p>Handle caption  </xd:p>
        </xd:desc>
    </xd:doc>
    <xsl:template match="hl7:caption">
        <xsl:choose>
            <xsl:when test="parent::hl7:table">
                <caption>
                    <xsl:apply-templates select="." mode="handleSectionTextAttributes"/>
                    <xsl:apply-templates/>
                </caption>
            </xsl:when>
            <xsl:otherwise>
                <div class="caption">
                    <xsl:apply-templates select="." mode="handleSectionTextAttributes"/>
                    <xsl:apply-templates/>
                </div>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>

    <xd:doc>
        <xd:desc>
            <xd:p>Handle footnote </xd:p>
        </xd:desc>
    </xd:doc>
    <xsl:template match="hl7:footnote">
        <xsl:variable name="id" select="@ID"/>
        <xsl:variable name="footNoteNum">
            <xsl:for-each select="//hl7:footnote">
                <xsl:if test="@ID = $id">
                    <xsl:value-of select="position()"/>
                </xsl:if>
            </xsl:for-each>
        </xsl:variable>
        <div>
            <xsl:apply-templates select="." mode="handleSectionTextAttributes">
                <xsl:with-param name="class" select="'narr_footnote'"/>
            </xsl:apply-templates>
            <xsl:text>[</xsl:text>
            <xsl:value-of select="$footNoteNum"/>
            <xsl:text>]. </xsl:text>
            <xsl:apply-templates/>
        </div>
    </xsl:template>

    <xd:doc>
        <xd:desc>
            <xd:p>Handle footnoteRef. Produces a superscript [n] where n is the occurence number of this ref in the
                whole document. Also adds a title with the first 50 characters of th footnote on the number so you 
                don't have to navigate to the footnote and just continue to read.</xd:p>
        </xd:desc>
    </xd:doc>
    <xsl:template match="hl7:footnoteRef">
        <xsl:variable name="idref" select="@IDREF"/>
        <xsl:variable name="footNoteNum">
            <xsl:for-each select="//hl7:footnote">
                <xsl:if test="@ID = $idref">
                    <xsl:value-of select="position()"/>
                </xsl:if>
            </xsl:for-each>
        </xsl:variable>
        <xsl:variable name="footNoteText">
            <xsl:copy-of select="//hl7:footnote[@ID = $idref]//text()"/>
        </xsl:variable>
        <sup>
            <xsl:text>[</xsl:text>
            <a href="#{$idref}">
                <!-- Render footnoteref with the first 50 characters of the text -->
                <xsl:attribute name="title">
                    <xsl:value-of select="substring($footNoteText, 1, 50)"/>
                    <xsl:if test="string-length($footNoteText) > 50">
                        <xsl:text>...</xsl:text>
                    </xsl:if>
                </xsl:attribute>
                <xsl:value-of select="$footNoteNum"/>
            </a>
            <xsl:text>]</xsl:text>
        </sup>
    </xsl:template>
    
    <xd:doc>
        <xd:desc>Handle table and constituents of table</xd:desc>
    </xd:doc>
    <xsl:template match="hl7:table | hl7:thead | hl7:tfoot | hl7:tbody | hl7:colgroup | hl7:col | hl7:tr | hl7:th | hl7:td">
        <xsl:element name="{local-name()}">
            <xsl:apply-templates select="." mode="handleSectionTextAttributes"/>
            <xsl:apply-templates/>
        </xsl:element>
    </xsl:template>

    <xd:doc>
        <xd:desc>
            <xd:p>Handle RenderMultiMedia. This currently only handles GIF's and JPEG's. It could, however, be extended 
                by including other image MIME types in the predicate and/or by generating &lt;object&gt; or &lt;applet&gt; 
                tag with the correct params depending on the media type @ID =$imageRef referencedObject </xd:p>
        </xd:desc>
    </xd:doc>
    <xsl:template match="hl7:renderMultiMedia">
        <xsl:variable name="imageRefs" select="@referencedObject"/>
        <xsl:variable name="referencedObjects" select="ancestor::hl7:section//hl7:regionOfInterest[@ID = $imageRefs] | ancestor::hl7:section//hl7:observationMedia[@ID = $imageRefs]"/>
        <div>
            <xsl:apply-templates select="hl7:caption"/>
            <xsl:for-each select="$referencedObjects">
                <xsl:choose>
                    <xsl:when test="self::hl7:regionOfInterest">
                        <!-- What we actually would want is an svg with fallback to just the image that renders the ROI on top of image
                            The only example (in the CDA standard itself) that we've seen so far has unusable coordinates. That for now
                            is not very encouraging to put in the effort, so we just render the images for now
                        -->
                        <xsl:apply-templates select=".//hl7:observationMedia">
                        </xsl:apply-templates>
                    </xsl:when>
                    <!-- Here is where the direct MultiMedia image referencing goes -->
                    <xsl:when test="self::hl7:observationMedia">
                        <xsl:apply-templates select="."/>
                    </xsl:when>
                </xsl:choose>
            </xsl:for-each>
        </div>
    </xsl:template>

    <xd:doc>
        <xd:desc>
            <xd:p>Handle superscript</xd:p>
        </xd:desc>
    </xd:doc>
    <xsl:template match="hl7:sup">
        <sup>
            <xsl:apply-templates select="." mode="handleSectionTextAttributes"/>
            <xsl:apply-templates/>
        </sup>
    </xsl:template>
    
    <xd:doc>
        <xd:desc>
            <xd:p>Handle subscript</xd:p>
        </xd:desc>
    </xd:doc>
    <xsl:template match="hl7:sub">
        <sub>
            <xsl:apply-templates select="." mode="handleSectionTextAttributes"/>
            <xsl:apply-templates/>
        </sub>
    </xsl:template>
    
    <xd:doc>
        <xd:desc>
            <xd:p>Attribute processing for CDAr2 and CDAr3</xd:p>
        </xd:desc>
        <xd:param name="class">If valued then this gets added to potential other class codes</xd:param>
    </xd:doc>
    <xsl:template match="*" mode="handleSectionTextAttributes">        
        <xsl:variable name="classes">
            <xsl:if test="@revised">
                <xsl:text> </xsl:text>
                <xsl:text>revision_</xsl:text>
                <xsl:value-of select="@revised"/>
                <xsl:text>_final</xsl:text>
            </xsl:if>
            <xsl:if test="@styleCode">
                <xsl:text> </xsl:text>
                <xsl:value-of select="@styleCode"/>
            </xsl:if>
            <xsl:if test="@class">
                <xsl:text> </xsl:text>
                <xsl:value-of select="@class"/>
            </xsl:if>
        </xsl:variable>
        
        <xsl:variable name="elem-name" select="local-name(.)"/>
        
        <!-- Write @class attribute if there's data for it -->
        <xsl:if test="string-length(normalize-space($classes))>0">
            <xsl:attribute name="class">
                <xsl:value-of select="normalize-space($classes)"/>
            </xsl:attribute>
        </xsl:if>
        <!-- Write title with @revised (CDAr1 / CDAr2) prefixing to @title if one exists already -->
        <xsl:if test="@revised">
            <xsl:attribute name="title">
                <xsl:value-of select="normalize-space(concat(@revised,' ',@title))"/>
            </xsl:attribute>
        </xsl:if>
        <!-- Write default table cellspacing / cellpadding -->
        <xsl:if test="self::hl7:table">
            <xsl:if test="not(@cellspacing)">
                <xsl:attribute name="cellspacing">
                    <xsl:value-of select="'1'"/>
                </xsl:attribute>
            </xsl:if>
            <xsl:if test="not(@cellpadding)">
                <xsl:attribute name="cellpadding">
                    <xsl:value-of select="'1'"/>
                </xsl:attribute>
            </xsl:if>
        </xsl:if>
        
        <xsl:for-each select="@*">
            <xsl:sort select="local-name()" order="descending"/>
            <xsl:variable name="attr-name" select="local-name(.)"/>
            <xsl:variable name="attr-value" select="."/>
            <xsl:choose>
                <!-- Regular handling from here -->
                <xsl:when test="$attr-name = 'ID'">
                    <xsl:attribute name="id">
                        <xsl:value-of select="."/>
                    </xsl:attribute>
                </xsl:when>
                <xsl:when test="$attr-name = 'class'">
                    <!-- Already handled -->
                </xsl:when>
                <xsl:when test="$attr-name = 'revised'">
                    <!-- Already handled -->
                </xsl:when>
                <xsl:when test="$attr-name = 'styleCode'">
                    <!-- Already handled -->
                </xsl:when>
                <xsl:when test="$attr-name = 'ID'">
                    <!-- @ID should be handled in a name tag, so don't add here -->
                </xsl:when>
                <xsl:when test="$attr-name = 'IDREF'">
                    <!-- @IDREF doubtful. Should be in an href attribute, but doesn't hurt to add here -->
                    <xsl:attribute name="idref">
                        <xsl:value-of select="."/>
                    </xsl:attribute>
                </xsl:when>
                <xsl:when test="$attr-name = 'language'">
                    <xsl:attribute name="lang">
                        <xsl:value-of select="."/>
                    </xsl:attribute>
                </xsl:when>

                <!-- Table stuff -->
                <xsl:when test="$attr-name = 'border'">
                    <xsl:attribute name="border">
                        <xsl:value-of select="."/>
                    </xsl:attribute>
                </xsl:when>
                <xsl:when test="$attr-name = 'frame'">
                    <xsl:attribute name="frame">
                        <xsl:value-of select="."/>
                    </xsl:attribute>
                </xsl:when>
                <xsl:when test="$attr-name = 'rules'">
                    <xsl:attribute name="rules">
                        <xsl:value-of select="."/>
                    </xsl:attribute>
                </xsl:when>
                <xsl:when test="$attr-name = 'cellpadding'">
                    <xsl:attribute name="cellpadding">
                        <xsl:value-of select="."/>
                    </xsl:attribute>
                </xsl:when>
                <xsl:when test="$attr-name = 'cellspacing'">
                    <xsl:attribute name="cellspacing">
                        <xsl:value-of select="."/>
                    </xsl:attribute>
                </xsl:when>
                <xsl:when test="$attr-name = 'span'">
                    <xsl:attribute name="span">
                        <xsl:value-of select="."/>
                    </xsl:attribute>
                </xsl:when>
                <xsl:when test="$attr-name = 'summary'">
                    <xsl:attribute name="summary">
                        <xsl:value-of select="."/>
                    </xsl:attribute>
                </xsl:when>
                <xsl:when test="$attr-name = 'width'">
                    <xsl:attribute name="width">
                        <xsl:value-of select="."/>
                    </xsl:attribute>
                </xsl:when>
                <xsl:when test="$attr-name = 'align'">
                    <xsl:attribute name="align">
                        <xsl:value-of select="."/>
                    </xsl:attribute>
                </xsl:when>
                <xsl:when test="$attr-name = 'valign'">
                    <xsl:attribute name="valign">
                        <xsl:value-of select="."/>
                    </xsl:attribute>
                </xsl:when>
                <xsl:when test="$attr-name = 'char'">
                    <xsl:attribute name="char">
                        <xsl:value-of select="."/>
                    </xsl:attribute>
                </xsl:when>
                <xsl:when test="$attr-name = 'charoff'">
                    <xsl:attribute name="charoff">
                        <xsl:value-of select="."/>
                    </xsl:attribute>
                </xsl:when>
                <xsl:when test="$attr-name = 'abbr'">
                    <xsl:attribute name="abbr">
                        <xsl:value-of select="."/>
                    </xsl:attribute>
                </xsl:when>
                <xsl:when test="$attr-name = 'scope'">
                    <xsl:attribute name="scope">
                        <xsl:value-of select="."/>
                    </xsl:attribute>
                </xsl:when>
                <xsl:when test="$attr-name = 'headers'">
                    <xsl:attribute name="headers">
                        <xsl:value-of select="."/>
                    </xsl:attribute>
                </xsl:when>
                <xsl:when test="$attr-name = 'axis'">
                    <xsl:attribute name="axis">
                        <xsl:value-of select="."/>
                    </xsl:attribute>
                </xsl:when>
                <xsl:when test="$attr-name = 'colspan'">
                    <xsl:attribute name="colspan">
                        <xsl:value-of select="."/>
                    </xsl:attribute>
                </xsl:when>
                <xsl:when test="$attr-name = 'rowspan'">
                    <xsl:attribute name="rowspan">
                        <xsl:value-of select="."/>
                    </xsl:attribute>
                </xsl:when>

                <!-- LinkHTML stuff -->
                <xsl:when test="$attr-name = 'name'">
                    <xsl:attribute name="name">
                        <xsl:value-of select="."/>
                    </xsl:attribute>
                </xsl:when>
                <xsl:when test="$attr-name = 'rel'">
                    <xsl:attribute name="rel">
                        <xsl:value-of select="."/>
                    </xsl:attribute>
                </xsl:when>
                <xsl:when test="$attr-name = 'href'">
                    <xsl:attribute name="href">
                        <xsl:value-of select="."/>
                    </xsl:attribute>
                </xsl:when>
                <xsl:when test="$attr-name = 'title'">
                    <xsl:attribute name="title">
                        <xsl:value-of select="."/>
                    </xsl:attribute>
                </xsl:when>
                <xsl:when test="$attr-name = 'rev'">
                    <xsl:attribute name="rev">
                        <xsl:value-of select="."/>
                    </xsl:attribute>
                </xsl:when>
                <xsl:otherwise>
                    <!-- For CDAr3 we might get a slew of attributes not catered for explicitly, 
                        but supposedly HTML compatible so just could add them as-is -->
                    <!-- However... CDAr3 never happened and this poses a security risk, so ignore -->
                    <!--<xsl:attribute name="{$attr-name}">
                        <xsl:value-of select="."/>
                    </xsl:attribute>-->
                </xsl:otherwise>
            </xsl:choose>
        </xsl:for-each>
    </xsl:template>
</xsl:stylesheet>