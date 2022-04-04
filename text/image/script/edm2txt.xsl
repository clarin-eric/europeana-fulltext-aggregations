<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:xs="http://www.w3.org/2001/XMLSchema"
    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    xmlns:edm="http://www.europeana.eu/schemas/edm/"
    exclude-result-prefixes="xs"
    version="2.0">
    <xsl:output media-type="text/plain" 
        method="text"
        encoding="UTF-8" 
        omit-xml-declaration="yes" />
    
    <xsl:template match="/">
        <xsl:value-of select="/rdf:RDF/edm:FullTextResource/rdf:value"/>
    </xsl:template>
</xsl:stylesheet>
