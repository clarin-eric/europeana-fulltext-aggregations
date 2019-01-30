<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:oai="http://www.openarchives.org/OAI/2.0/"
    exclude-result-prefixes="xs oai" version="2.0">

    <xsl:param name="selectionDoc" required="yes" />

    <!-- load the index in a variable, document() can do GET requests, other HTTP verbs need an extension -->
    <xsl:variable name="idx" select="document($selectionDoc)"/>

    <!-- define the key (the index), which will work on any document 
     assumes the GET request returns an XML document with <record identifier="..."/> elements -->
    <xsl:key name="index" match="record" use="@identifier"/>

    <!-- lookup the processed record in the index, and if so copy it -->
    <xsl:template match="oai:record[key('index', oai:header/oai:identifier, $idx/records)]"
        priority="1">
        <xsl:copy-of select="."/>
    </xsl:template>

    <!-- do nothing for records not found in the index -->
    <xsl:template match="oai:record"/>

    <xsl:template match="oai:OAI-PMH">

        <OAI-PMH
            xmlns="http://www.openarchives.org/OAI/2.0/"
            xsi:schemaLocation="http://www.openarchives.org/OAI/2.0/ http://www.openarchives.org/OAI/2.0/OAI-PMH.xsd">
            <xsl:copy-of select="oai:responseDate" />
            <xsl:copy-of select="oai:request" />
            <ListRecords>
                <xsl:apply-templates select="/oai:OAI-PMH/oai:ListRecords/oai:record"/>
            </ListRecords>
        </OAI-PMH>

    </xsl:template>

</xsl:stylesheet>
