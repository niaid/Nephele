## Nephele
Nephele is a Microbiome Cloud Pilot project developed and managed by the Bioinformatics and Computational Biosciences Branch ([BCBB](http://www.niaid.nih.gov/about/organization/odoffices/omo/ocicb/pages/bcbb.aspx)), which is part of the National Institute of Allergy and Infectious Diseases (NIAID).

Nephele intends to allow non-expert users to process microbiome datasets through a pipeline of existing software tools. Typically this type of work is computationally intensive, and also demands knowledge of both scripting and the tools themselves. Nephele attempts to address these issues.

To address the computationally intensive aspect, we provision dedicated, cloud-based compute resources, in an on-demand nature and with an appropriate environment for analyzing user-supplied data. When an analysis pipeline completes, this compute resource is torn down. This means users can process as many datasets as they choose, simultaneously, by machines that are dynamically spun up and shut down.

To ease the learning curve of installing, configuring, and running the software, we stitch together a series of computational tasks into a number of prepared generic pipelines. Pipelines are configured using inputs from simple web-front-end forms, which allow users to specify commonly-changed parameters. We combine these with sensible default parameters, when appropriate.

It is important to note that *all* of the software which comprises Nephele--for example [mothur](http://www.mothur.org/), [QIIME](http://qiime.org/), [bioBakery](https://bitbucket.org/biobakery/biobakery/wiki/Home), and [a5-miseq](https://sourceforge.net/projects/ngopt/)--is freely available for use. We do not attempt to supersede or act as a replacement for this software, nor do we modify it. Nephele instead attempts to take a number of useful tools and provide them to a wider audience. We recommend visiting the software creators' websites for details of their implementation. To examine how we use these tools, users can explore this repository as well as view log files that accompany each job and detail how each component of the pipeline was executed.

Nephele's pipelines have been collated from a number of sources, and all are being actively worked on.

Nephele currently uses Amazon's EC2 platform as a compute resource with curated machine images. We use Amazon's S3 service to store pipeline results for a period of time.

We would like to thank all contributors to this project, and are grateful for feedback.

## Public Domain license

This is free and unencumbered software released into the public domain. 
</br>*Be kind, and provide attribution when you use this code.*

United States government creative works, including writing, images, and computer code, are usually prepared by officers or employees of the United States government as part of their official duties. A government work is generally not subject to copyright in the United States and there is generally no copyright restriction on reproduction, derivative works, distribution, performance, or display of a government work. Unless the work falls under an exception, anyone may, without restriction under U.S. copyright laws:

* Reproduce the work in print or digital form
* Create derivative works
* Perform the work publicly
* Display the work
* Distribute copies or digitally transfer the work to the public by sale or other transfer of ownership, or by rental, lease, or lending

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.

Learn more about how copyright applies to U.S. government works at [USA.gov](https://www.usa.gov/government-works)


## Attribution for Third-Party Software

Please also report the publication of articles which made use of Nephele by providing the reference in an [email to the Nephele Project Team](mailto:NEPHELESUPPORT@ocicb-bcbb.atlassian.net?Subject=Nephele Help).

* * *

## For QIIME or mothur (16s or 18s) please cite both of the following along with Nephele:

**Download Citations:**  

[EndNote](https://s3.amazonaws.com/nephele-pipelines-development/userdocs/QIIME_mothur.enw)  
[RIS](https://s3.amazonaws.com/nephele-pipelines-development/userdocs/QIIME_mothur.RIS)  
[BIB](https://s3.amazonaws.com/nephele-pipelines-development/userdocs/QIIME_mothur.bib)

**mothur**  
Schloss PD, Westcott SL, Ryabin T, Hall JR, Hartmann M, Hollister EB, Lesniewski RA, Oakley BB, Parks DH, Robinson CJ, Sahl JW, Stres B, Thallinger GG, Van Horn DJ, Weber CF. Introducing mothur: Open-source, platform-independent, community-supported software for describing and comparing microbial communities. Appl Environ Microbiol. 2009;75(23):7537-41.

**QIIME**  
Caporaso JG, Kuczynski J, Stombaugh J, Bittinger K, Bushman FD, Costello EK, Fierer N, Gonzalez Pena A, Goodrich JK, Gordon JI, Huttley GA, Kelley ST, Knights D, Koenig JE, Ley RE, Lozupone CA, McDonald D, Muegge BD, Pirrung M, Reeder J, Sevinsky JR, Turnbaugh PJ, Walters WA, Widmann J, Yatsunenko T, Zaneveld J, Knight R. QIIME allows analysis of high-throughput community sequencing data. Nature Methods. 2010;7(5):335-336.,  
[qiime.org](http://www.qiime.org/)  

QIIME uses multiple open source software tools that should also be cited. Please see "Citing QIIME" on the above link for details.

## BioBakery pipeline (WGS)

**Download Citations:**  

[EndNote](https://s3.amazonaws.com/nephele-pipelines-development/userdocs/biobakery.enw)  
[RIS](https://s3.amazonaws.com/nephele-pipelines-development/userdocs/biobakery.RIS)  
[BIB](https://s3.amazonaws.com/nephele-pipelines-development/userdocs/biobakery.bib)  

Huttenhower C. Huttenhower Lab Tools [Internet]. Cambridge (MA): The Huttenhower Lab Department of Biostatistics, Harvard T.H. Chan School of Public Health; 2015 July 15 [cited 2015 Sep 16]. Available from [https://bitbucket.org/biobakery/biobakery/wiki/Home](https://bitbucket.org/biobakery/biobakery/wiki/Home)

## A5-miseq (WGS)

**Download Citations:**  

[EndNote](https://s3.amazonaws.com/nephele-pipelines-development/userdocs/a5.enw)  
[RIS](https://s3.amazonaws.com/nephele-pipelines-development/userdocs/a5.RIS)  
[BIB](https://s3.amazonaws.com/nephele-pipelines-development/userdocs/a5.bib)  

Coil D, Jospin G, Darling AE. A5-miseq: An updated pipeline to assemble microbial genomes from Illumina MiSeq data. Bioinformatics. 2015;31(4):587-589.
